import { CapabilityExchange } from "./capabilities";
import { sessionProof } from "./session_proof";

type Socket = Pick<WebSocket, "send" | "close" | "addEventListener">;
type Proof = Awaited<ReturnType<typeof sessionProof>>;
export type ConnectionConfig = {
  port: number; credentialId: string; credentialSecret: string; pinnedIdentity: string;
};

export class ExtensionConnection {
  private socket: Socket | null = null;
  private generation = 0;
  private phase: "closed" | "challenge" | "authenticated" | "capabilities" | "ready" = "closed";
  private pendingProof: Proof | null = null;
  private epoch = 0;
  private queue: Promise<void> = Promise.resolve();
  private exchange = new CapabilityExchange(frame => this.send(frame));

  constructor(
    private readonly config: ConnectionConfig,
    private readonly factory: (url: string) => Socket = url => new WebSocket(url),
    private readonly cryptoApi: Crypto = crypto,
  ) {
    if (!Number.isInteger(config.port) || config.port < 1 || config.port > 65535) throw new Error("INVALID_PORT");
  }

  connect(): void {
    this.disconnect();
    const generation = this.generation;
    const socket = this.factory(`wss://127.0.0.1:${this.config.port}/extension/v1`);
    this.socket = socket;
    socket.addEventListener("open", () => {
      if (generation !== this.generation) return;
      this.phase = "challenge";
      try { this.send({ type: "authenticate", payload: { credential_id: this.config.credentialId } }); }
      catch { this.disconnect(); }
    });
    socket.addEventListener("message", event => {
      this.queue = this.queue.then(async () => {
        if (generation !== this.generation) return;
        await this.receive((event as MessageEvent).data, generation);
      }).catch(() => { if (generation === this.generation) this.disconnect(); });
    });
    for (const event of ["close", "error"]) socket.addEventListener(event, () => {
      if (generation === this.generation) this.disconnect();
    });
  }

  disconnect(): void {
    const socket = this.socket;
    this.socket = null;
    this.generation += 1;
    this.phase = "closed";
    this.pendingProof = null;
    this.exchange.reset();
    socket?.close();
  }

  status(): { connected: boolean; capabilitiesReported: boolean; executionReady: false } {
    return { connected: this.phase === "ready", ...this.exchange.status() };
  }

  // Also useful for deterministic transport tests; does not establish readiness.
  async settled(): Promise<void> { await this.queue; }

  private send(frame: unknown): void {
    if (!this.socket) throw new Error("DISCONNECTED");
    this.socket.send(JSON.stringify(frame));
  }

  private async receive(raw: unknown, generation: number): Promise<void> {
    if (typeof raw !== "string" || new TextEncoder().encode(raw).length > 1048576) throw new Error("INVALID_FRAME");
    const frame = JSON.parse(raw);
    if (!frame || Object.keys(frame).sort().join() !== "payload,type" || !frame.payload ||
        typeof frame.payload !== "object" || Array.isArray(frame.payload)) throw new Error("INVALID_FRAME");
    const payload = frame.payload;
    if (this.phase === "challenge" && frame.type === "challenge") {
      if (Object.keys(payload).sort().join() !== "challenge_id,nonce") throw new Error("INVALID_CHALLENGE");
      const proof = await sessionProof(this.config.credentialId, payload.challenge_id, payload.nonce,
        this.config.credentialSecret, this.config.pinnedIdentity, this.cryptoApi);
      if (generation !== this.generation) return;
      this.pendingProof = proof;
      this.phase = "authenticated";
      this.send({ type: "proof", payload: proof.payload });
    } else if (this.phase === "authenticated" && frame.type === "authenticated" && this.pendingProof) {
      if (Object.keys(payload).sort().join() !== "expires_at,principal_id,signature" ||
          typeof payload.principal_id !== "string" || !/^[0-9a-f-]{36}$/.test(payload.principal_id) ||
          typeof payload.expires_at !== "string" || !Number.isFinite(Date.parse(payload.expires_at)) ||
          Date.parse(payload.expires_at) <= Date.now()) throw new Error("INVALID_SESSION");
      await this.pendingProof.verify(payload.signature);
      if (generation !== this.generation) return;
      this.pendingProof = null;
      this.epoch = this.exchange.verifiedSession();
      this.phase = "capabilities";
      // No browser handlers have been implemented or qualified yet.
      this.exchange.report(this.epoch, [], []);
    } else if (this.phase === "capabilities" && frame.type === "capabilities_received") {
      this.exchange.acknowledge(this.epoch, frame);
      this.phase = "ready";
    } else if (this.phase === "ready" && frame.type === "heartbeat" && Object.keys(payload).length === 0) {
      return;
    } else {
      throw new Error("UNEXPECTED_FRAME");
    }
  }
}
