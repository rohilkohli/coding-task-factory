// Hidden feature tests for the jsoncpp "allowSpecialFloats" reader task.
// Built with the upstream jsontest harness into its own test binary; each
// requirement in instruction.md has at least one test here.
#include "jsontest.h"
#include <json/json.h>

#include <cmath>
#include <cstring>
#include <limits>
#include <memory>
#include <string>

static std::deque<JsonTest::TestCaseFactory> local_;
#define JSONTEST_FIXTURE_LOCAL(FixtureType, name)                              \
  JSONTEST_FIXTURE_V2(FixtureType, name, local_)

namespace {

const double kInf = std::numeric_limits<double>::infinity();

bool parse(const Json::CharReaderBuilder& builder, const std::string& doc,
           Json::Value* root, Json::String* errs) {
  std::unique_ptr<Json::CharReader> reader(builder.newCharReader());
  return reader->parse(doc.data(), doc.data() + doc.size(), root, errs);
}

Json::CharReaderBuilder specialFloats() {
  Json::CharReaderBuilder builder;
  builder.settings_["allowSpecialFloats"] = true;
  return builder;
}

} // namespace

struct SpecialFloatsSettings : JsonTest::TestCase {};

JSONTEST_FIXTURE_LOCAL(SpecialFloatsSettings, defaultsIncludeSettingAsFalse) {
  Json::Value settings;
  Json::CharReaderBuilder::setDefaults(&settings);
  JSONTEST_ASSERT(settings.isMember("allowSpecialFloats"));
  JSONTEST_ASSERT_EQUAL(false, settings["allowSpecialFloats"].asBool());
}

JSONTEST_FIXTURE_LOCAL(SpecialFloatsSettings, strictAndEcma404ModesDisableIt) {
  Json::Value strict;
  Json::CharReaderBuilder::strictMode(&strict);
  JSONTEST_ASSERT(strict.isMember("allowSpecialFloats"));
  JSONTEST_ASSERT_EQUAL(false, strict["allowSpecialFloats"].asBool());

  Json::Value ecma;
  Json::CharReaderBuilder::ecma404Mode(&ecma);
  JSONTEST_ASSERT(ecma.isMember("allowSpecialFloats"));
  JSONTEST_ASSERT_EQUAL(false, ecma["allowSpecialFloats"].asBool());
}

JSONTEST_FIXTURE_LOCAL(SpecialFloatsSettings, validateAcceptsTheKey) {
  Json::CharReaderBuilder builder = specialFloats();
  Json::Value invalid;
  JSONTEST_ASSERT(builder.validate(&invalid));
  JSONTEST_ASSERT_EQUAL(0u, invalid.size());

  builder.settings_["allowSpecialFloatz"] = true; // a typo is still rejected
  JSONTEST_ASSERT(!builder.validate(&invalid));
  JSONTEST_ASSERT(invalid.isMember("allowSpecialFloatz"));
}

struct SpecialFloatsDisabled : JsonTest::TestCase {};

JSONTEST_FIXTURE_LOCAL(SpecialFloatsDisabled, rejectedByDefault) {
  Json::CharReaderBuilder builder;
  const char* docs[] = {"{\"a\": NaN}", "{\"a\": Infinity}",
                        "{\"a\": -Infinity}", "{\"a\": +Infinity}", "[NaN]",
                        "[-Infinity]"};
  for (const char* doc : docs) {
    Json::Value root;
    Json::String errs;
    JSONTEST_ASSERT(!parse(builder, doc, &root, &errs)) << doc;
    JSONTEST_ASSERT(!errs.empty()) << doc;
  }
}

JSONTEST_FIXTURE_LOCAL(SpecialFloatsDisabled, defaultErrorMessages) {
  Json::CharReaderBuilder builder;
  Json::Value root;
  Json::String errs;
  JSONTEST_ASSERT(!parse(builder, "{\"a\": NaN}", &root, &errs));
  JSONTEST_ASSERT_STRING_EQUAL(
      "* Line 1, Column 7\n"
      "  Syntax error: value, object or array expected.\n",
      errs);
  JSONTEST_ASSERT(!parse(builder, "[Infinity]", &root, &errs));
  JSONTEST_ASSERT_STRING_EQUAL(
      "* Line 1, Column 2\n"
      "  Syntax error: value, object or array expected.\n",
      errs);
}

JSONTEST_FIXTURE_LOCAL(SpecialFloatsDisabled, ordinaryNumbersStillParse) {
  Json::CharReaderBuilder builder;
  Json::Value root;
  Json::String errs;
  JSONTEST_ASSERT(parse(builder, "[-12, -1.5e-3, 0, 7, -0.25]", &root, &errs))
      << errs;
  JSONTEST_ASSERT_EQUAL(-12, root[0].asInt());
  JSONTEST_ASSERT_EQUAL(-1.5e-3, root[1].asDouble());
  JSONTEST_ASSERT_EQUAL(7, root[3].asInt());
  JSONTEST_ASSERT_EQUAL(-0.25, root[4].asDouble());
}

struct SpecialFloatsEnabled : JsonTest::TestCase {};

JSONTEST_FIXTURE_LOCAL(SpecialFloatsEnabled, parsesAllFourSpellings) {
  Json::Value root;
  Json::String errs;
  JSONTEST_ASSERT(parse(specialFloats(),
                        R"({"nan": NaN, "inf": Infinity, "neg": -Infinity, "pos": +Infinity})",
                        &root, &errs))
      << errs;
  JSONTEST_ASSERT_STRING_EQUAL("", errs);
  JSONTEST_ASSERT(root["nan"].isDouble());
  JSONTEST_ASSERT(std::isnan(root["nan"].asDouble()));
  JSONTEST_ASSERT(root["inf"].isDouble());
  JSONTEST_ASSERT_EQUAL(kInf, root["inf"].asDouble());
  JSONTEST_ASSERT_EQUAL(-kInf, root["neg"].asDouble());
  JSONTEST_ASSERT_EQUAL(kInf, root["pos"].asDouble());
}

JSONTEST_FIXTURE_LOCAL(SpecialFloatsEnabled, worksInArraysAndAtTopLevel) {
  Json::Value root;
  Json::String errs;
  JSONTEST_ASSERT(parse(specialFloats(), "[NaN, -Infinity, 1.5, -2, Infinity]",
                        &root, &errs))
      << errs;
  JSONTEST_ASSERT_EQUAL(5u, root.size());
  JSONTEST_ASSERT(std::isnan(root[0].asDouble()));
  JSONTEST_ASSERT_EQUAL(-kInf, root[1].asDouble());
  JSONTEST_ASSERT_EQUAL(1.5, root[2].asDouble());
  JSONTEST_ASSERT_EQUAL(-2, root[3].asInt());
  JSONTEST_ASSERT_EQUAL(kInf, root[4].asDouble());

  JSONTEST_ASSERT(parse(specialFloats(), "-Infinity", &root, &errs)) << errs;
  JSONTEST_ASSERT_EQUAL(-kInf, root.asDouble());
  JSONTEST_ASSERT(parse(specialFloats(), "NaN", &root, &errs)) << errs;
  JSONTEST_ASSERT(std::isnan(root.asDouble()));
}

JSONTEST_FIXTURE_LOCAL(SpecialFloatsEnabled, ordinaryNumbersUnaffected) {
  Json::Value root;
  Json::String errs;
  JSONTEST_ASSERT(parse(specialFloats(), "[-12, -1.5e-3, 0, 7, -0.25, 1e2]",
                        &root, &errs))
      << errs;
  JSONTEST_ASSERT_EQUAL(-12, root[0].asInt());
  JSONTEST_ASSERT_EQUAL(-1.5e-3, root[1].asDouble());
  JSONTEST_ASSERT_EQUAL(0, root[2].asInt());
  JSONTEST_ASSERT_EQUAL(-0.25, root[4].asDouble());
  JSONTEST_ASSERT_EQUAL(100.0, root[5].asDouble());
}

JSONTEST_FIXTURE_LOCAL(SpecialFloatsEnabled, spellingIsExactAndCaseSensitive) {
  const char* docs[] = {
      "[nan]",       "[NAN]",       "[Nan]",         "[infinity]",
      "[INFINITY]",  "[Inf]",       "[-Inf]",        "[Infinit]",
      "[NaNa]",      "[Infinityy]", "[- Infinity]",  "[+ Infinity]",
      "[--Infinity]", "[1Infinity]", "[.Infinity]",  "[-NaN]"};
  for (const char* doc : docs) {
    Json::Value root;
    Json::String errs;
    JSONTEST_ASSERT(!parse(specialFloats(), doc, &root, &errs)) << doc;
  }
}

JSONTEST_FIXTURE_LOCAL(SpecialFloatsEnabled, recordsValueOffsets) {
  Json::Value root;
  Json::String errs;
  const std::string doc = R"({"a":NaN,"b":-Infinity,"c":+Infinity})";
  JSONTEST_ASSERT(parse(specialFloats(), doc, &root, &errs)) << errs;
  JSONTEST_ASSERT_EQUAL(5, root["a"].getOffsetStart());
  JSONTEST_ASSERT_EQUAL(8, root["a"].getOffsetLimit());
  JSONTEST_ASSERT_EQUAL(13, root["b"].getOffsetStart());
  JSONTEST_ASSERT_EQUAL(22, root["b"].getOffsetLimit());
  JSONTEST_ASSERT_EQUAL(27, root["c"].getOffsetStart());
  JSONTEST_ASSERT_EQUAL(36, root["c"].getOffsetLimit());
}

JSONTEST_FIXTURE_LOCAL(SpecialFloatsEnabled, roundTripsWithWriterSpecialFloats) {
  Json::Value original(Json::arrayValue);
  original.append(std::numeric_limits<double>::quiet_NaN());
  original.append(kInf);
  original.append(-kInf);

  Json::StreamWriterBuilder writer;
  writer["useSpecialFloats"] = true;
  writer["indentation"] = "";
  const Json::String text = Json::writeString(writer, original);
  JSONTEST_ASSERT_STRING_EQUAL("[NaN,Infinity,-Infinity]", text);

  Json::Value back;
  Json::String errs;
  JSONTEST_ASSERT(parse(specialFloats(), text, &back, &errs)) << errs;
  JSONTEST_ASSERT(std::isnan(back[0].asDouble()));
  JSONTEST_ASSERT_EQUAL(kInf, back[1].asDouble());
  JSONTEST_ASSERT_EQUAL(-kInf, back[2].asDouble());
}

JSONTEST_FIXTURE_LOCAL(SpecialFloatsEnabled, combinesWithOtherSettings) {
  Json::CharReaderBuilder builder = specialFloats();
  builder.settings_["allowComments"] = true;
  builder.settings_["allowTrailingCommas"] = true;
  Json::Value root;
  Json::String errs;
  JSONTEST_ASSERT(parse(builder, "[NaN, /* c */ -Infinity, ] // end", &root,
                        &errs))
      << errs;
  JSONTEST_ASSERT_EQUAL(2u, root.size());
  JSONTEST_ASSERT_EQUAL(-kInf, root[1].asDouble());
}

int main(int argc, const char* argv[]) {
  JsonTest::Runner runner;
  for (auto& local : local_) {
    runner.add(local);
  }
  return runner.runCommandLine(argc, argv);
}
