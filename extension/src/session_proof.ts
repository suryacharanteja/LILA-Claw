// Application identity proof over the approved length-prefixed transcript.
const encoder = new TextEncoder();

export function encode(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes)).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

export function decode(value: string, size: number): Uint8Array<ArrayBuffer> {
  if (typeof value !== "string" || !/^[A-Za-z0-9_-]+$/.test(value)) throw new Error("INVALID_PROOF_ENCODING");
  const bytes = Uint8Array.from(atob(value.replaceAll("-", "+").replaceAll("_", "/")), char => char.charCodeAt(0));
  if (bytes.length !== size || encode(bytes) !== value) throw new Error("INVALID_PROOF_ENCODING");
  return bytes;
}

export function transcript(parts: Uint8Array[]): Uint8Array<ArrayBuffer> {
  const result = new Uint8Array(parts.reduce((size, part) => size + 4 + part.length, 0));
  const view = new DataView(result.buffer);
  let offset = 0;
  for (const part of parts) {
    view.setUint32(offset, part.length, false);
    result.set(part, offset + 4);
    offset += 4 + part.length;
  }
  return result;
}

export async function sessionProof(
  credentialId: string, challengeId: string, serverNonce: string,
  credentialSecret: string, pinnedIdentity: string,
  cryptoApi: Crypto = crypto,
): Promise<{ payload: { client_nonce: string; proof: string }; verify: (signature: string) => Promise<void> }> {
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
  if (!uuid.test(credentialId) || !uuid.test(challengeId)) throw new Error("INVALID_CHALLENGE");
  const nonce = decode(serverNonce, 32);
  const secret = decode(credentialSecret, 32);
  const identity = decode(pinnedIdentity, 32);
  const clientNonce = cryptoApi.getRandomValues(new Uint8Array(32));
  const value = transcript([encoder.encode("lila-extension-v1"), encoder.encode(credentialId), encoder.encode(challengeId), nonce, clientNonce]);
  let key: CryptoKey;
  try {
    key = await cryptoApi.subtle.importKey("raw", secret, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  } finally {
    secret.fill(0);
  }
  const proof = new Uint8Array(await cryptoApi.subtle.sign("HMAC", key, value));
  const signed = new Uint8Array(value.length + proof.length);
  signed.set(value);
  signed.set(proof, value.length);
  const digest = await cryptoApi.subtle.digest("SHA-256", signed);
  const publicKey = await cryptoApi.subtle.importKey("raw", identity, "Ed25519", false, ["verify"]);
  let consumed = false;
  return {
    payload: { client_nonce: encode(clientNonce), proof: encode(proof) },
    verify: async signature => {
      if (consumed) throw new Error("PROOF_ALREADY_CONSUMED");
      consumed = true;
      if (!await cryptoApi.subtle.verify("Ed25519", publicKey, decode(signature, 64), digest)) {
        throw new Error("SERVER_IDENTITY_MISMATCH");
      }
    },
  };
}
