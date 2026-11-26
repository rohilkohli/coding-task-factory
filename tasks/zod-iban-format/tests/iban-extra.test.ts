// Hidden feature tests for the zod IBAN task. They complement the upstream
// tests (classic/tests/iban.test.ts and the "z.iban" case in
// mini/tests/string.test.ts) and pin down each requirement in instruction.md.
import { describe, expect, expectTypeOf, test } from "vitest";
import * as z from "zod";
import * as zm from "zod/mini";

const VALID = "DE89370400440532013000";
const BAD_CHECKSUM = "DE89370400440532013001";

describe("z.iban (extended)", () => {
  test("is exported from classic, mini and core", () => {
    expect(typeof z.iban).toBe("function");
    expect(typeof zm.iban).toBe("function");
    expect(typeof z.core._iban).toBe("function");
    expect(typeof z.core.$ZodIBAN).toBe("function");
    expect(typeof z.core.isValidIBAN).toBe("function");
  });

  test("creates a string-format schema with format 'iban'", () => {
    const schema = z.iban();
    expect(schema).toBeInstanceOf(z.ZodIBAN);
    expect(schema).toBeInstanceOf(z.ZodStringFormat);
    expect(schema.format).toBe("iban");
    expect(schema._zod.def.format).toBe("iban");
    expectTypeOf(schema).toEqualTypeOf<z.ZodIBAN>();
    expectTypeOf<z.infer<typeof schema>>().toEqualTypeOf<string>();
  });

  test("core isValidIBAN checks shape and mod-97 checksum", () => {
    expect(z.core.isValidIBAN(VALID)).toBe(true);
    expect(z.core.isValidIBAN("NO9386011117947")).toBe(true);
    expect(z.core.isValidIBAN(BAD_CHECKSUM)).toBe(false);
    expect(z.core.isValidIBAN(VALID.toLowerCase())).toBe(false);
    expect(z.core.isValidIBAN("DE00000000000000000066")).toBe(false);
  });

  test("enforces the 15-34 length bounds even when the checksum is valid", () => {
    // Each value has correct check digits, so only the length rule can reject it.
    const checksumValidButWrongLength = [
      "AA90AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", // 35
      "AA70BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", // 36
      "AA211234567890", // 14
      "AA92ABCDEFGHIJ", // 14
    ];
    for (const value of checksumValidButWrongLength) {
      expect(z.iban().safeParse(value).success).toBe(false);
      expect(z.core.isValidIBAN(value)).toBe(false);
      expect(z.regexes.iban.test(value)).toBe(false);
    }
  });

  test("letters in the BBAN take part in the checksum", () => {
    expect(z.iban().safeParse("GB29NWBK60161331926819").success).toBe(true);
    expect(z.iban().safeParse("GB29NWBK60161331926818").success).toBe(false);
    expect(z.iban().safeParse("MT84MALT011000012345MTLCAST001S").success).toBe(true);
    expect(z.iban().safeParse("MT84MALT011000012345MTLCAST001T").success).toBe(false);
  });

  test("reports an invalid_format issue with format 'iban'", () => {
    const result = z.iban().safeParse(BAD_CHECKSUM);
    expect(result.success).toBe(false);
    expect(result.error!.issues).toHaveLength(1);
    expect(result.error!.issues[0]).toMatchObject({
      code: "invalid_format",
      format: "iban",
      path: [],
      message: "Invalid IBAN",
    });
  });

  test("does not abort later checks unless abort: true is set", () => {
    const codes = (r: { error?: { issues: { code: string }[] } }) => r.error!.issues.map((i) => i.code);
    expect(codes(z.iban().max(10).safeParse(BAD_CHECKSUM))).toEqual(["invalid_format", "too_big"]);
    expect(codes(z.iban({ abort: true }).max(10).safeParse(BAD_CHECKSUM))).toEqual(["invalid_format"]);
    expect(codes(z.string().check(z.iban(), z.maxLength(10)).safeParse(BAD_CHECKSUM))).toEqual([
      "invalid_format",
      "too_big",
    ]);
  });

  test("supports custom error messages", () => {
    expect(z.iban("Bad IBAN").safeParse("nope").error!.issues[0]!.message).toBe("Bad IBAN");
    expect(z.iban({ error: "Still bad" }).safeParse("nope").error!.issues[0]!.message).toBe("Still bad");
  });

  test("rejects non-string input as invalid_type", () => {
    expect(z.iban().safeParse(12345).error!.issues[0]!.code).toBe("invalid_type");
  });

  test("works as a check on z.string()", () => {
    const schema = z.string().check(z.iban());
    expect(schema.safeParse(VALID).success).toBe(true);
    expect(schema.safeParse(BAD_CHECKSUM).success).toBe(false);
  });

  test("composes with optional and inside objects", () => {
    expect(z.iban().optional().safeParse(undefined).success).toBe(true);
    const account = z.object({ iban: z.iban() });
    expect(account.safeParse({ iban: VALID }).success).toBe(true);
    const bad = account.safeParse({ iban: BAD_CHECKSUM });
    expect(bad.success).toBe(false);
    expect(bad.error!.issues[0]!.path).toEqual(["iban"]);
  });

  test("regexes.iban describes the shape only", () => {
    expect(z.regexes.iban).toBeInstanceOf(RegExp);
    expect(z.regexes.iban.test(VALID)).toBe(true);
    expect(z.regexes.iban.test(BAD_CHECKSUM)).toBe(true); // checksum is not a pattern
    expect(z.regexes.iban.test("DE00000000000000000066")).toBe(false);
    expect(z.regexes.iban.test("DE01000000000000000048")).toBe(false);
    expect(z.regexes.iban.test("DE99000000000000000030")).toBe(false);
    expect(z.regexes.iban.test(VALID.toLowerCase())).toBe(false);
    expect(z.regexes.iban.test("NO938601111794")).toBe(false);
  });

  test("compiled schemas enforce the checksum", () => {
    const compiled = z.compile(z.iban());
    expect(compiled.safeParse(VALID).success).toBe(true);
    expect(compiled.safeParse(BAD_CHECKSUM).success).toBe(false);
    expect(compiled.safeParse(VALID.toLowerCase()).success).toBe(false);
    expect(() => z.compile(z.iban(), { strict: true })).not.toThrow();

    const compiledObject = z.compile(z.object({ iban: z.iban() }));
    expect(compiledObject.safeParse({ iban: VALID }).success).toBe(true);
    expect(compiledObject.safeParse({ iban: BAD_CHECKSUM }).success).toBe(false);
  });

  test("zod/mini enforces shape and checksum", () => {
    const schema = zm.iban();
    expect(zm.safeParse(schema, VALID).success).toBe(true);
    const bad = zm.safeParse(schema, BAD_CHECKSUM);
    expect(bad.success).toBe(false);
    expect(bad.error!.issues[0]).toMatchObject({ code: "invalid_format", format: "iban" });
    expect(zm.safeParse(schema, "de89370400440532013000").success).toBe(false);
  });

  test("JSON Schema export and import keep the IBAN semantics", () => {
    const jsonSchema = z.toJSONSchema(z.iban());
    expect(jsonSchema).toMatchObject({ type: "string", format: "iban", pattern: z.regexes.iban.source });
    const roundTripped = z.fromJSONSchema({ type: "string", format: "iban" });
    expect(roundTripped.safeParse("NO9386011117947").success).toBe(true);
    expect(roundTripped.safeParse("NO9386011117948").success).toBe(false);
  });
});
