import { isRTL } from "@/i18n.config";

describe("i18n config", () => {
  it("marks Hebrew as RTL", () => {
    expect(isRTL("he")).toBe(true);
  });

  it("marks English as LTR", () => {
    expect(isRTL("en")).toBe(false);
  });
});
