#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace {

const std::vector<std::string> required = {
    "seq_order", "classification_id", "anon_name", "metadata",
    "subject_ids", "classification", "classifier"};

std::vector<std::string> parse_csv_record(const std::string& input) {
    std::vector<std::string> fields;
    std::string current;
    bool quoted = false;
    for (std::size_t i = 0; i < input.size(); ++i) {
        const char ch = input[i];
        if (quoted) {
            if (ch == '"') {
                if (i + 1 < input.size() && input[i + 1] == '"') {
                    current.push_back('"');
                    ++i;
                } else {
                    quoted = false;
                }
            } else {
                current.push_back(ch);
            }
        } else if (ch == '"') {
            if (!current.empty()) throw std::runtime_error("quote inside unquoted CSV field");
            quoted = true;
        } else if (ch == ',') {
            fields.push_back(current);
            current.clear();
        } else {
            current.push_back(ch);
        }
    }
    if (quoted) throw std::runtime_error("unterminated quoted CSV field");
    fields.push_back(current);
    return fields;
}

void write_csv_field(std::ostream& out, const std::string& value) {
    const bool quote = value.find_first_of(",\"\r\n") != std::string::npos;
    if (!quote) {
        out << value;
        return;
    }
    out << '"';
    for (char ch : value) {
        if (ch == '"') out << '"';
        out << ch;
    }
    out << '"';
}

std::string normalize(std::string value) {
    if (value.size() >= 3 && static_cast<unsigned char>(value[0]) == 0xef &&
        static_cast<unsigned char>(value[1]) == 0xbb &&
        static_cast<unsigned char>(value[2]) == 0xbf) {
        value.erase(0, 3);
    }
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char ch) {
        return static_cast<char>(std::tolower(ch));
    });
    return value;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: redact_infection_inspection OUTPUT.csv\n";
        return 2;
    }
    std::ofstream output(argv[1], std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open output\n";
        return 2;
    }
    try {
        std::string record;
        if (!std::getline(std::cin, record)) throw std::runtime_error("empty source CSV");
        if (!record.empty() && record.back() == '\r') record.pop_back();
        const auto header = parse_csv_record(record);
        std::unordered_map<std::string, std::size_t> positions;
        for (std::size_t i = 0; i < header.size(); ++i) positions[normalize(header[i])] = i;
        for (const auto& name : required) {
            if (positions.count(name) != 1) throw std::runtime_error("missing required field: " + name);
        }
        for (std::size_t i = 0; i < required.size(); ++i) {
            if (i) output << ',';
            output << required[i];
        }
        output << '\n';

        std::uint64_t rows = 0;
        while (std::getline(std::cin, record)) {
            if (!record.empty() && record.back() == '\r') record.pop_back();
            const auto fields = parse_csv_record(record);
            if (fields.size() != header.size()) throw std::runtime_error("unexpected source field count");
            for (std::size_t i = 0; i < required.size(); ++i) {
                if (i) output << ',';
                write_csv_field(output, fields[positions.at(required[i])]);
            }
            output << '\n';
            ++rows;
        }
        output.flush();
        if (!output) throw std::runtime_error("write failure");
        std::cerr << "redacted_rows=" << rows << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "redaction_error=" << error.what() << "\n";
        output.close();
        std::remove(argv[1]);
        return 1;
    }
}
