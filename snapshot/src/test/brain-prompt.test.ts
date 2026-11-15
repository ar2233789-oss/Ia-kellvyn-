import { beforeEach, describe, expect, it } from "vitest";
import { buildSystemPrompt } from "../components/kellvyn/brainPrompt";

describe("Kellvyn system prompt and reinforced protection", () => {
  beforeEach(() => localStorage.clear());

  it("enables reinforced protection by default, matching Android's initial setting", () => {
    expect(buildSystemPrompt()).toContain("PROTEÇÃO REFORÇADA ATIVADA:");
  });

  it("omits only reinforced rules when the existing toggle is disabled", () => {
    const prompt = buildSystemPrompt(false);
    expect(prompt).toContain("Você é Kellvyn IA");
    expect(prompt).not.toContain("PROTEÇÃO REFORÇADA ATIVADA:");
  });

  it("includes saved memories as context without replacing the core rules", () => {
    localStorage.setItem("kv.memories", JSON.stringify([{ id: "1", text: "Prefere português brasileiro." }]));
    const prompt = buildSystemPrompt(true);
    expect(prompt).toContain("Prefere português brasileiro.");
    expect(prompt).toContain("PROTEÇÃO REFORÇADA ATIVADA:");
    expect(prompt).toContain("Você é Kellvyn IA");
  });

  it("caps memory count and individual memory length", () => {
    const records = Array.from({ length: 35 }, (_, index) => ({
      id: String(index),
      text: index === 0 ? "X".repeat(400) : "Memória " + index,
    }));
    localStorage.setItem("kv.memories", JSON.stringify(records));
    const prompt = buildSystemPrompt(false);
    expect(prompt).toContain("X".repeat(300));
    expect(prompt).not.toContain("X".repeat(301));
    expect(prompt).not.toContain("Memória 30");
  });
});
