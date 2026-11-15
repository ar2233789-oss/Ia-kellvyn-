/**
 * Local Gemma runtime for the Lovable preview.
 *
 * Model inference stays on this device. The SDK is downloaded as JavaScript;
 * prompts and generated text are not sent to a hosted AI service.
 * The web SDK currently supports text input/output only.
 */
import { buildSystemPrompt } from "./brainPrompt";
import { prepareUserText } from "./webContext";

type HistoryTurn = {
  role: "user" | "assistant";
  text: string;
  error?: boolean | undefined;
};

type StreamItem = { type?: string; text?: string };
type StreamChunk = { content?: StreamItem[] };

type LocalConversation = {
  sendMessageStreaming: (text: string) => AsyncIterable<StreamChunk>;
  cancel?: () => void;
};

type LocalEngine = {
  createConversation: (config: unknown) => Promise<LocalConversation>;
  delete?: () => Promise<void>;
};

type EngineModule = {
  Engine: {
    create: (config: unknown) => Promise<LocalEngine>;
  };
  SamplerType: { TOP_P: unknown };
};

type OpfsFileHandle = {
  getFile: () => Promise<File>;
  createWritable: () => Promise<WritableStream<Uint8Array>>;
};

type IncrementalSha256 = {
  update: (chunk: Uint8Array) => IncrementalSha256;
  digest: () => Uint8Array;
};

type Sha256Module = {
  sha256: { create: () => IncrementalSha256 };
};

type OpfsDirectoryHandle = {
  getFileHandle: (name: string, options?: { create?: boolean }) => Promise<OpfsFileHandle>;
};

type StorageWithOpfs = {
  getDirectory?: () => Promise<OpfsDirectoryHandle>;
  estimate?: () => Promise<{ quota?: number; usage?: number }>;
  persist?: () => Promise<boolean>;
};

const MODEL_URL =
  "https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm/resolve/41c5569623a7c189d6eec3e5225260c58cedbce7/gemma-4-E2B-it-gpu.litertlm";
const SDK_URL = "https://cdn.jsdelivr.net/npm/@litert-lm/core@0.18.0/+esm";
const SHA256_URL = "https://cdn.jsdelivr.net/npm/@noble/hashes@2.0.0/sha2.js/+esm";
const MODEL_FILE_NAME = "kellvyn-gemma-4-e2b-gpu.litertlm";
const MODEL_HASH_FILE_NAME = MODEL_FILE_NAME + ".sha256";
const EXPECTED_MODEL_BYTES = 2_008_432_640;
const EXPECTED_MODEL_SHA256 = "a53a59001894c58e6bdb5b9b227709f91a2e3e556baa7d85acf9c55402ba5cf5";
const STORAGE_MARGIN_BYTES = 64 * 1024 * 1024;

let enginePromise: Promise<LocalEngine> | null = null;
let sdkPromise: Promise<EngineModule> | null = null;
let sha256Promise: Promise<Sha256Module> | null = null;
type CachedConversation = { instance: LocalConversation; strongProtection: boolean };
const conversations = new Map<string, CachedConversation>();

async function getSdk(): Promise<EngineModule> {
  if (!sdkPromise) {
    const moduleUrl: string = SDK_URL;
    sdkPromise = import(/* @vite-ignore */ moduleUrl) as Promise<EngineModule>;
  }
  try {
    return await sdkPromise;
  } catch (error) {
    sdkPromise = null;
    throw error;
  }
}

function requireBrowserSupport() {
  if (typeof window === "undefined" || typeof navigator === "undefined") {
    throw new Error("O motor local só pode ser iniciado no navegador.");
  }
  if (!window.isSecureContext) {
    throw new Error("Abra a prévia em uma conexão HTTPS segura para iniciar a IA local.");
  }
  const gpu = (navigator as Navigator & { gpu?: unknown }).gpu;
  if (!gpu) {
    throw new Error("Este navegador não disponibiliza WebGPU. Abra a prévia atualizada no Chrome do Poco F6.");
  }
}

async function getSha256Module(): Promise<Sha256Module> {
  if (!sha256Promise) {
    const moduleUrl: string = SHA256_URL;
    sha256Promise = import(/* @vite-ignore */ moduleUrl) as Promise<Sha256Module>;
  }
  try {
    return await sha256Promise;
  } catch (error) {
    sha256Promise = null;
    throw error;
  }
}

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
}

async function hashFile(file: File): Promise<string> {
  const { sha256 } = await getSha256Module();
  const hasher = sha256.create();
  const reader = file.stream().getReader();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (value) hasher.update(value);
    }
  } finally {
    reader.releaseLock();
  }
  return toHex(hasher.digest());
}

async function saveHashMarker(directory: OpfsDirectoryHandle, digest: string): Promise<void> {
  const marker = await directory.getFileHandle(MODEL_HASH_FILE_NAME, { create: true });
  const writable = await marker.createWritable();
  await new Blob([digest], { type: "text/plain" }).stream().pipeTo(writable);
}

async function getModelSource(): Promise<string | File> {
  const storage = navigator.storage as unknown as StorageWithOpfs;
  if (!storage.getDirectory) {
    throw new Error("Este navegador não oferece armazenamento local verificável para preparar a IA. Abra o Kellvyn no Chrome atualizado.");
  }

  const directory = await storage.getDirectory();
  const handle = await directory.getFileHandle(MODEL_FILE_NAME, { create: true });
  const hashHandle = await directory.getFileHandle(MODEL_HASH_FILE_NAME, { create: true });
  const cached = await handle.getFile();

  if (cached.size === EXPECTED_MODEL_BYTES) {
    const marker = await (await hashHandle.getFile()).text();
    if (marker.trim() === EXPECTED_MODEL_SHA256) return cached;

    // Verify an existing cache before trusting it; save a marker to avoid rehashing on every launch.
    const cachedHash = await hashFile(cached);
    if (cachedHash === EXPECTED_MODEL_SHA256) {
      await saveHashMarker(directory, cachedHash);
      return cached;
    }
  }

  const estimate = await storage.estimate?.();
  if (
    estimate?.quota &&
    estimate.usage !== undefined &&
    estimate.quota - estimate.usage < EXPECTED_MODEL_BYTES + STORAGE_MARGIN_BYTES
  ) {
    throw new Error("Não há espaço livre suficiente no armazenamento local para preparar o modelo de IA de aproximadamente 2,01 GB.");
  }

  await storage.persist?.();
  const response = await fetch(MODEL_URL, { cache: "force-cache" });
  if (!response.ok || !response.body) {
    throw new Error("Não consegui baixar o modelo local Gemma 4 E2B. Verifique a conexão do celular e tente novamente.");
  }

  const expectedSize = Number(response.headers.get("content-length") ?? "0");
  if (expectedSize > 0 && expectedSize !== EXPECTED_MODEL_BYTES) {
    throw new Error("O servidor enviou um arquivo de modelo com tamanho diferente da revisão aprovada. O download foi interrompido.");
  }

  const { sha256 } = await getSha256Module();
  const hasher = sha256.create();
  let transferredBytes = 0;
  const verifyStream = new TransformStream<Uint8Array, Uint8Array>({
    transform(chunk, controller) {
      transferredBytes += chunk.byteLength;
      if (transferredBytes > EXPECTED_MODEL_BYTES) {
        throw new Error("O arquivo do modelo excedeu o tamanho esperado; download interrompido.");
      }
      hasher.update(chunk);
      controller.enqueue(chunk);
    },
  });

  const writable = await handle.createWritable();
  await response.body.pipeThrough(verifyStream).pipeTo(writable);

  const downloaded = await handle.getFile();
  if (downloaded.size !== EXPECTED_MODEL_BYTES || transferredBytes !== EXPECTED_MODEL_BYTES) {
    throw new Error("A transferência do modelo ficou incompleta. Envie a mensagem novamente para tentar de novo.");
  }

  const downloadedHash = toHex(hasher.digest());
  if (downloadedHash !== EXPECTED_MODEL_SHA256) {
    throw new Error("A verificação SHA-256 do modelo local falhou. O arquivo não será carregado; tente baixar novamente.");
  }

  await saveHashMarker(directory, downloadedHash);
  return downloaded;
}
async function getEngine(): Promise<LocalEngine> {
  if (enginePromise) return enginePromise;

  enginePromise = (async () => {
    requireBrowserSupport();
    // Load the LiteRT-LM web runtime at runtime so the UI bundle stays unchanged.
    const sdk = await getSdk();
    const model = await getModelSource();
    return sdk.Engine.create({
      model,
      mainExecutorSettings: { maxNumTokens: 4096 },
    });
  })();

  try {
    return await enginePromise;
  } catch (error) {
    enginePromise = null;
    throw error;
  }
}

function makeConversationConfig(
  samplerType: unknown,
  history: HistoryTurn[],
  strongProtection: boolean,
): unknown {
  const messages = [
    { role: "system", content: buildSystemPrompt(strongProtection) },
    ...history
      .filter((turn) => !turn.error && turn.text.trim())
      .slice(-12)
      .map((turn) => ({ role: turn.role, content: turn.text })),
  ];

  return {
    preface: { messages },
    sessionConfig: {
      maxOutputTokens: 1536,
      samplerParams: {
        type: samplerType,
        temperature: 0.6,
        p: 0.9,
        k: 40,
      },
    },
    prefillPrefaceOnInit: true,
    filterChannelContentFromKvCache: true,
  };
}

export async function askLocalBrain(
  conversationId: string,
  userText: string,
  history: HistoryTurn[],
  onPartial: (text: string) => void,
  strongProtection = true,
): Promise<string> {
  const engine = await getEngine();
  const sdk = await getSdk();

  const cached = conversations.get(conversationId);
  let conversation = cached?.strongProtection === strongProtection ? cached.instance : undefined;
  if (cached && !conversation) {
    cached.instance.cancel?.();
    conversations.delete(conversationId);
  }
  if (!conversation) {
    conversation = await engine.createConversation(
      makeConversationConfig(sdk.SamplerType.TOP_P, history, strongProtection),
    );
    conversations.set(conversationId, { instance: conversation, strongProtection });

    // Keep only a few live chat contexts to limit memory usage on phones.
    while (conversations.size > 4) {
      const oldestKey = conversations.keys().next().value as string | undefined;
      if (!oldestKey || oldestKey === conversationId) break;
      conversations.get(oldestKey)?.instance.cancel?.();
      conversations.delete(oldestKey);
    }
  }

  // Build guidelines and Web context are added here; the chat screen still shows the original text.
  const outgoing = await prepareUserText(userText);

  let output = "";
  for await (const chunk of conversation.sendMessageStreaming(outgoing)) {
    for (const item of chunk.content ?? []) {
      if (item.type === "text" || (!item.type && typeof item.text === "string")) {
        output += item.text ?? "";
        onPartial(output);
      }
    }
  }

  const finalText = output.trim();
  if (!finalText) {
    throw new Error("O modelo local terminou sem produzir uma resposta. Tente enviar a mensagem novamente.");
  }
  return finalText;
}

export function textFromAttachment(attachment: {
  name: string;
  type: string;
  dataUrl: string;
}): string {
  const extension = attachment.name.split(".").pop()?.toLowerCase() ?? "";
  const textExtensions = new Set([
    "txt", "md", "json", "kt", "java", "ts", "tsx", "js", "jsx", "xml", "html", "css", "py",
  ]);
  if (
    !attachment.type.startsWith("text/") &&
    !textExtensions.has(extension) &&
    attachment.type !== "application/json"
  ) {
    throw new Error("Esta prévia do motor Web aceita anexos de texto e código. A leitura local de imagens e PDFs pertence à versão Android nativa.");
  }

  const encoded = attachment.dataUrl.split(",")[1];
  if (!encoded) throw new Error("Não consegui ler o arquivo anexado.");
  const binary = atob(encoded);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  const content = new TextDecoder("utf-8").decode(bytes);
  if (!content.trim()) throw new Error("O arquivo anexado não contém texto legível.");
  return content.slice(0, 120_000);
}
