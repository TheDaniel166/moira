#ifndef MOIRA_NATIVE_DAF_HPP
#define MOIRA_NATIVE_DAF_HPP

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace moira {
namespace native {

struct DafSummaryEntry {
    std::string name;
    double start_second;
    double end_second;
    int32_t target;
    int32_t center;
    int32_t frame;
    int32_t data_type;
    int32_t start_i;
    int32_t end_i;
};

struct DafCatalog {
    std::string locidw;
    std::string locfmt;
    uint32_t nd;
    uint32_t ni;
    uint32_t fward;
    uint32_t bward;
    uint32_t free;
    bool little_endian;
    std::vector<DafSummaryEntry> summaries;
};

struct SpkChebyshevSegmentPayload {
    double init;
    double intlen;
    int32_t record_size;
    int32_t record_count;
    int32_t component_count;
    int32_t coefficient_count;
    std::vector<double> coefficients;
};

struct SpkType13SegmentPayload {
    int32_t state_count;
    int32_t window_size;
    std::vector<double> states;
    std::vector<double> epochs_jd;
};

namespace detail {

inline uint32_t byteswap_u32(uint32_t value) {
    return ((value & 0x000000FFu) << 24) |
           ((value & 0x0000FF00u) << 8) |
           ((value & 0x00FF0000u) >> 8) |
           ((value & 0xFF000000u) >> 24);
}

inline uint64_t byteswap_u64(uint64_t value) {
    return ((value & 0x00000000000000FFull) << 56) |
           ((value & 0x000000000000FF00ull) << 40) |
           ((value & 0x0000000000FF0000ull) << 24) |
           ((value & 0x00000000FF000000ull) << 8) |
           ((value & 0x000000FF00000000ull) >> 8) |
           ((value & 0x0000FF0000000000ull) >> 24) |
           ((value & 0x00FF000000000000ull) >> 40) |
           ((value & 0xFF00000000000000ull) >> 56);
}

inline uint32_t read_u32(const char* ptr, bool little_endian) {
    uint32_t value = 0;
    std::memcpy(&value, ptr, sizeof(value));
#if defined(_WIN32)
    constexpr bool host_little_endian = true;
#else
    const uint16_t test = 0x0100;
    const bool host_little_endian = *reinterpret_cast<const uint8_t*>(&test) == 0x00;
#endif
    if (host_little_endian != little_endian) {
        value = byteswap_u32(value);
    }
    return value;
}

inline uint64_t read_u64(const char* ptr, bool little_endian) {
    uint64_t value = 0;
    std::memcpy(&value, ptr, sizeof(value));
#if defined(_WIN32)
    constexpr bool host_little_endian = true;
#else
    const uint16_t test = 0x0100;
    const bool host_little_endian = *reinterpret_cast<const uint8_t*>(&test) == 0x00;
#endif
    if (host_little_endian != little_endian) {
        value = byteswap_u64(value);
    }
    return value;
}

inline double read_f64(const char* ptr, bool little_endian) {
    const uint64_t bits = read_u64(ptr, little_endian);
    double value = 0.0;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

inline std::string strip_trailing(const std::string& value, char trim_char) {
    size_t end = value.size();
    while (end > 0 && value[end - 1] == trim_char) {
        --end;
    }
    return value.substr(0, end);
}

inline std::string strip_ascii_space(const std::string& value) {
    size_t start = 0;
    while (start < value.size() && value[start] == ' ') {
        ++start;
    }
    size_t end = value.size();
    while (end > start && value[end - 1] == ' ') {
        --end;
    }
    return value.substr(start, end - start);
}

inline std::array<char, 1024> read_record(std::ifstream& file, uint32_t record_number) {
    std::array<char, 1024> buffer{};
    const std::streamoff offset = static_cast<std::streamoff>(record_number - 1) * 1024;
    file.seekg(offset, std::ios::beg);
    if (!file.good()) {
        throw std::runtime_error("failed to seek DAF record");
    }
    file.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
    if (file.gcount() != static_cast<std::streamsize>(buffer.size())) {
        throw std::runtime_error("failed to read full DAF record");
    }
    return buffer;
}

inline std::pair<std::string, bool> detect_format(const std::array<char, 1024>& file_record) {
    const std::string locidw = strip_trailing(std::string(file_record.data(), 8), ' ');
    if (locidw == "NAIF/DAF") {
        const uint32_t nd_little = read_u32(file_record.data() + 8, true);
        if (nd_little == 2u) {
            return {"LTL-IEEE", true};
        }
        const uint32_t nd_big = read_u32(file_record.data() + 8, false);
        if (nd_big == 2u) {
            return {"BIG-IEEE", false};
        }
        throw std::runtime_error("unable to determine endianness for NAIF/DAF file");
    }
    if (locidw.rfind("DAF/", 0) == 0) {
        const std::string locfmt = strip_trailing(std::string(file_record.data() + 88, 8), ' ');
        if (locfmt == "LTL-IEEE") {
            return {locfmt, true};
        }
        if (locfmt == "BIG-IEEE") {
            return {locfmt, false};
        }
        throw std::runtime_error("unsupported DAF format marker");
    }
    throw std::runtime_error("file is not a recognized DAF/SPK kernel");
}

} // namespace detail

inline DafCatalog read_daf_catalog(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("unable to open DAF file");
    }

    const auto file_record = detail::read_record(file, 1);
    const std::string locidw = detail::strip_trailing(std::string(file_record.data(), 8), ' ');
    const auto [locfmt, little_endian] = detail::detect_format(file_record);

    DafCatalog catalog;
    catalog.locidw = locidw;
    catalog.locfmt = locfmt;
    catalog.little_endian = little_endian;
    catalog.nd = detail::read_u32(file_record.data() + 8, little_endian);
    catalog.ni = detail::read_u32(file_record.data() + 12, little_endian);
    catalog.fward = detail::read_u32(file_record.data() + 76, little_endian);
    catalog.bward = detail::read_u32(file_record.data() + 80, little_endian);
    catalog.free = detail::read_u32(file_record.data() + 84, little_endian);

    const size_t summary_length = static_cast<size_t>(catalog.nd) * 8 + static_cast<size_t>(catalog.ni) * 4;
    const size_t summary_step = summary_length + ((8 - (summary_length % 8)) % 8);

    uint32_t record_number = catalog.fward;
    while (record_number != 0) {
        const auto summary_record = detail::read_record(file, record_number);
        const auto name_record = detail::read_record(file, record_number + 1);

        const uint32_t next_record = static_cast<uint32_t>(
            detail::read_f64(summary_record.data(), little_endian)
        );
        const uint32_t n_summaries = static_cast<uint32_t>(
            detail::read_f64(summary_record.data() + 16, little_endian)
        );

        for (uint32_t summary_index = 0; summary_index < n_summaries; ++summary_index) {
            const size_t summary_offset = 24 + static_cast<size_t>(summary_index) * summary_step;
            const size_t name_offset = static_cast<size_t>(summary_index) * summary_step;
            const char* summary_ptr = summary_record.data() + summary_offset;
            const char* name_ptr = name_record.data() + name_offset;

            DafSummaryEntry entry;
            entry.name = detail::strip_ascii_space(std::string(name_ptr, summary_step));
            entry.start_second = detail::read_f64(summary_ptr, little_endian);
            entry.end_second = detail::read_f64(summary_ptr + 8, little_endian);
            entry.target = static_cast<int32_t>(detail::read_u32(summary_ptr + 16, little_endian));
            entry.center = static_cast<int32_t>(detail::read_u32(summary_ptr + 20, little_endian));
            entry.frame = static_cast<int32_t>(detail::read_u32(summary_ptr + 24, little_endian));
            entry.data_type = static_cast<int32_t>(detail::read_u32(summary_ptr + 28, little_endian));
            entry.start_i = static_cast<int32_t>(detail::read_u32(summary_ptr + 32, little_endian));
            entry.end_i = static_cast<int32_t>(detail::read_u32(summary_ptr + 36, little_endian));
            catalog.summaries.push_back(std::move(entry));
        }

        record_number = next_record;
    }

    return catalog;
}

inline SpkChebyshevSegmentPayload read_spk_chebyshev_segment_payload(
    const std::string& path,
    int32_t start_i,
    int32_t end_i,
    bool little_endian,
    int32_t data_type
) {
    int32_t component_count = 0;
    if (data_type == 2) {
        component_count = 3;
    } else if (data_type == 3) {
        component_count = 6;
    } else {
        throw std::runtime_error("only SPK type 2 and type 3 payloads are supported");
    }

    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("unable to open DAF file");
    }

    const auto read_word = [&](int32_t word_index) -> double {
        const std::streamoff offset = static_cast<std::streamoff>(word_index - 1) * 8;
        file.seekg(offset, std::ios::beg);
        if (!file.good()) {
            throw std::runtime_error("failed to seek DAF word");
        }
        std::array<char, 8> buffer{};
        file.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
        if (file.gcount() != static_cast<std::streamsize>(buffer.size())) {
            throw std::runtime_error("failed to read DAF word");
        }
        return detail::read_f64(buffer.data(), little_endian);
    };

    const double init = read_word(end_i - 3);
    const double intlen = read_word(end_i - 2);
    const int32_t record_size = static_cast<int32_t>(read_word(end_i - 1));
    const int32_t record_count = static_cast<int32_t>(read_word(end_i));
    if (record_size <= 2 || record_count <= 0) {
        throw std::runtime_error("invalid SPK record sizing in segment payload");
    }

    const int32_t coefficient_count = (record_size - 2) / component_count;
    if (coefficient_count <= 0) {
        throw std::runtime_error("invalid SPK coefficient count in segment payload");
    }

    const int64_t coefficient_word_count = static_cast<int64_t>(record_count) * record_size;
    const std::streamoff coeff_offset = static_cast<std::streamoff>(start_i - 1) * 8;
    const std::streamsize coeff_bytes = static_cast<std::streamsize>(coefficient_word_count * 8);

    file.seekg(coeff_offset, std::ios::beg);
    if (!file.good()) {
        throw std::runtime_error("failed to seek SPK coefficient payload");
    }

    std::vector<char> raw_bytes(static_cast<size_t>(coeff_bytes));
    file.read(raw_bytes.data(), coeff_bytes);
    if (file.gcount() != coeff_bytes) {
        throw std::runtime_error("failed to read SPK coefficient payload");
    }

    SpkChebyshevSegmentPayload payload;
    payload.init = init;
    payload.intlen = intlen;
    payload.record_size = record_size;
    payload.record_count = record_count;
    payload.component_count = component_count;
    payload.coefficient_count = coefficient_count;
    payload.coefficients.resize(static_cast<size_t>(coefficient_count) * component_count * record_count);

    for (int32_t record_index = 0; record_index < record_count; ++record_index) {
        const int32_t record_word_base = record_index * record_size;
        for (int32_t component_index = 0; component_index < component_count; ++component_index) {
            for (int32_t coefficient_index = 0; coefficient_index < coefficient_count; ++coefficient_index) {
                const int32_t source_word_index = record_word_base + 2 + component_index * coefficient_count + coefficient_index;
                const char* ptr = raw_bytes.data() + static_cast<size_t>(source_word_index) * 8;
                const double value = detail::read_f64(ptr, little_endian);

                const size_t dest_index =
                    (static_cast<size_t>(record_index) * component_count + static_cast<size_t>(component_index))
                    * static_cast<size_t>(coefficient_count)
                    + static_cast<size_t>(coefficient_count - 1 - coefficient_index);
                payload.coefficients[dest_index] = value;
            }
        }
    }

    return payload;
}

inline SpkType13SegmentPayload read_spk_type13_segment_payload(
    const std::string& path,
    int32_t start_i,
    int32_t end_i,
    bool little_endian
) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("unable to open DAF file");
    }

    const auto read_word = [&](int32_t word_index) -> double {
        const std::streamoff offset = static_cast<std::streamoff>(word_index - 1) * 8;
        file.seekg(offset, std::ios::beg);
        if (!file.good()) {
            throw std::runtime_error("failed to seek DAF word");
        }
        std::array<char, 8> buffer{};
        file.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
        if (file.gcount() != static_cast<std::streamsize>(buffer.size())) {
            throw std::runtime_error("failed to read DAF word");
        }
        return detail::read_f64(buffer.data(), little_endian);
    };

    const int32_t window_size = static_cast<int32_t>(read_word(end_i - 1));
    const int32_t state_count = static_cast<int32_t>(read_word(end_i));
    if (state_count <= 0 || window_size <= 0) {
        throw std::runtime_error("invalid SPK type 13 payload sizing");
    }

    const int32_t directory_count = (state_count - 1) / 100;
    const int64_t expected_word_count =
        static_cast<int64_t>(7) * state_count + directory_count + 2;
    const int64_t actual_word_count =
        static_cast<int64_t>(end_i) - static_cast<int64_t>(start_i) + 1;
    if (expected_word_count != actual_word_count) {
        throw std::runtime_error("SPK type 13 payload length does not match descriptor bounds");
    }

    const int64_t state_word_count = static_cast<int64_t>(6) * state_count;
    const int64_t epoch_word_count = state_count;
    const std::streamoff payload_offset = static_cast<std::streamoff>(start_i - 1) * 8;
    const std::streamsize payload_bytes = static_cast<std::streamsize>(
        (state_word_count + epoch_word_count) * 8
    );

    file.seekg(payload_offset, std::ios::beg);
    if (!file.good()) {
        throw std::runtime_error("failed to seek SPK type 13 payload");
    }

    std::vector<char> raw_bytes(static_cast<size_t>(payload_bytes));
    file.read(raw_bytes.data(), payload_bytes);
    if (file.gcount() != payload_bytes) {
        throw std::runtime_error("failed to read SPK type 13 payload");
    }

    SpkType13SegmentPayload payload;
    payload.state_count = state_count;
    payload.window_size = window_size;
    payload.states.resize(static_cast<size_t>(6) * state_count);
    payload.epochs_jd.resize(static_cast<size_t>(state_count));

    for (int32_t row = 0; row < state_count; ++row) {
        for (int32_t axis = 0; axis < 6; ++axis) {
            const int64_t source_index = static_cast<int64_t>(row) * 6 + axis;
            const char* ptr = raw_bytes.data() + static_cast<size_t>(source_index) * 8;
            payload.states[static_cast<size_t>(axis) * state_count + row] =
                detail::read_f64(ptr, little_endian);
        }
    }

    const size_t epoch_byte_offset = static_cast<size_t>(state_word_count) * 8;
    for (int32_t idx = 0; idx < state_count; ++idx) {
        const char* ptr = raw_bytes.data() + epoch_byte_offset + static_cast<size_t>(idx) * 8;
        payload.epochs_jd[static_cast<size_t>(idx)] =
            detail::read_f64(ptr, little_endian) / 86400.0 + 2451545.0;
    }

    return payload;
}

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_DAF_HPP
