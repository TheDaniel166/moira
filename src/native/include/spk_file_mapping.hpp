#ifndef MOIRA_NATIVE_SPK_FILE_MAPPING_HPP
#define MOIRA_NATIVE_SPK_FILE_MAPPING_HPP

#include <cstddef>
#include <cstdio>

namespace moira {
namespace native {

// A read-only view of the same open file used for buffered SPK reads.
// Like cached records, the view assumes the kernel stays immutable.
class SpkFileMapping {
public:
    explicit SpkFileMapping(std::FILE* file) noexcept;
    ~SpkFileMapping();

    SpkFileMapping(const SpkFileMapping&) = delete;
    SpkFileMapping& operator=(const SpkFileMapping&) = delete;

    const char* bytes(std::size_t offset, std::size_t count) const noexcept {
        if (view_ == nullptr || offset > size_ || count > size_ - offset) {
            return nullptr;
        }
        return static_cast<const char*>(view_) + offset;
    }

private:
    void* view_ = nullptr;
    std::size_t size_ = 0;
};

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_SPK_FILE_MAPPING_HPP
