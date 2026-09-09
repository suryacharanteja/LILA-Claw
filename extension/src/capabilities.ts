// Session-bound capability exchange. Pairing/proof verification is a separate layer.
export const toolNames = [
  "inspect_context", "discover_jobs", "inspect_form", "fill_fields",
  "attach_document", "advance_step", "submit_application", "inspect_outcome",
] as const;
export type BrowserTool = typeof toolNames[number];
export type CapabilityReport = {
  protocol_version: 1;
  tools: BrowserTool[];
  adapter_ids: string[];
};

export function reportCapabilities(tools: readonly BrowserTool[], adapters: readonly string[]): CapabilityReport {
  if (tools.length > 8 || new Set(tools).size !== tools.length ||
      tools.some(tool => !toolNames.includes(tool)) || adapters.length > 32 ||
      new Set(adapters).size !== adapters.length ||
      adapters.some(id => !/^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$/.test(id))) {
    throw new Error("INVALID_CAPABILITIES");
  }
  return { protocol_version: 1, tools: [...tools], adapter_ids: [...adapters] };
}

export class CapabilityExchange {
  private epoch = 0;
  private authenticated = false;
  private pending = false;
  private accepted = false;

  constructor(private readonly send: (frame: unknown) => void) {}

  // Called only after the pairing layer verifies the server's session proof.
  // A socket message named "authenticated" alone must not invoke this method.
  verifiedSession(): number {
    this.reset();
    this.authenticated = true;
    return this.epoch;
  }

  reset(): void {
    this.epoch += 1;
    this.authenticated = false;
    this.pending = false;
    this.accepted = false;
  }

  report(epoch: number, tools: readonly BrowserTool[], adapters: readonly string[]): void {
    if (!this.authenticated || epoch !== this.epoch || this.pending || this.accepted) {
      throw new Error("CAPABILITY_SESSION_REQUIRED");
    }
    const payload = reportCapabilities(tools, adapters);
    this.pending = true;
    try {
      this.send({ type: "capabilities", payload });
    } catch (error) {
      this.reset();
      throw error;
    }
  }

  acknowledge(epoch: number, frame: unknown): void {
    if (!this.authenticated || epoch !== this.epoch || !this.pending) {
      throw new Error("STALE_CAPABILITY_ACKNOWLEDGEMENT");
    }
    const value = frame as { type?: unknown; payload?: Record<string, unknown> } | null;
    if (!value || typeof value !== "object" || Object.keys(value).sort().join() !== "payload,type" ||
        value.type !== "capabilities_received" || !value.payload ||
        Object.keys(value.payload).sort().join() !== "accepted,execution_ready" ||
        value.payload.accepted !== true || value.payload.execution_ready !== false) {
      this.reset();
      throw new Error("INVALID_CAPABILITY_ACKNOWLEDGEMENT");
    }
    this.pending = false;
    this.accepted = true;
  }

  status(): { capabilitiesReported: boolean; executionReady: false } {
    return { capabilitiesReported: this.accepted, executionReady: false };
  }
}
