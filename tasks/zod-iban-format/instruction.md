We want Zod to validate International Bank Account Numbers (IBANs) as a built-in string format, the same way it already supports formats like `z.email()` and `z.creditCard()`. The repository is in `/app` and the library source is in `/app/packages/zod/src`. The format name `"iban"` and its localized labels (for example `"IBAN"` in the English locale) already exist. The validator itself is missing.

Add an IBAN string format with the following behaviour.

**Validation rules** (electronic format only):
- Input must be a string of 2 uppercase letters (country code), then 2 check digits, then 11–30 uppercase letters or digits. That makes the total length 15–34.
- Lowercase letters, spaces, hyphens and any other characters are rejected.
- The check digits must be between `02` and `98`, so `00`, `01` and `99` are rejected.
- The ISO 7064 mod 97-10 checksum must hold. Move the first four characters to the end, convert letters to numbers (`A` = 10 … `Z` = 35), and the resulting number mod 97 must equal 1. Don't depend on `BigInt`.

**API surface:**
- **core:** a regex `regexes.iban` that checks the shape only (the checksum can't be a pattern). A helper `isValidIBAN(input: string): boolean` that applies the shape and checksum rules. A `$ZodIBAN` schema constructor and an `_iban(Class, params?)` factory, following the pattern of the other string formats. Also add params types and an entry in the string-format types union.
- **classic (`zod`):** `z.iban(params?)` returning a `ZodIBAN` schema. It is a `ZodStringFormat` with `format === "iban"`, and it accepts the usual string or `{ error }` params. It must also work as a check, for example `z.string().check(z.iban())`.
- **mini (`zod/mini`):** `iban(params?)` returning a `ZodMiniIBAN`.
- **Errors:** a failed value produces a single `invalid_format` issue with `format: "iban"`. With the default English locale the message is `Invalid IBAN`. As with the other formats, a failure doesn't stop later checks (for example `.max(10)`) from running and reporting, unless the schema was created with `abort: true`.
- **JSON Schema:** `z.toJSONSchema(z.iban())` emits `{ type: "string", format: "iban", pattern: <regexes.iban source> }`. `z.fromJSONSchema` maps `format: "iban"` back to a schema that also enforces the checksum.
- **Compiled schemas:** `z.compile(...)` must give the same results as the runtime parser for IBAN schemas, including rejecting a wrong checksum, both standalone and nested in objects.

Follow the conventions of the neighbouring string formats (especially credit cards), and keep the existing test suite green. Run the tests from `/app` with `npx vitest run --project zod` (add `--typecheck.enabled=false` for a faster runtime-only pass).
