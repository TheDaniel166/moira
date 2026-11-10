#include "spk_file_mapping.hpp"

#include <cstdint>
#include <limits>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <io.h>
#include <windows.h>
#elif defined(__unix__) || defined(__APPLE__)
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

namespace moira {
namespace native {

namespace {

bool addressable(std::uintmax_t size) noexcept {
    return size <= static_cast<std::uintmax_t>(std::numeric_limits<std::ptrdiff_t>::max());
}

} // namespace

SpkFileMapping::SpkFileMapping(std::FILE* file) noexcept {
#ifdef _WIN32
    const auto handle = reinterpret_cast<HANDLE>(::_get_osfhandle(::_fileno(file)));
    LARGE_INTEGER length;
    if (handle == INVALID_HANDLE_VALUE || !::GetFileSizeEx(handle, &length)
        || length.QuadPart <= 0 || !addressable(length.QuadPart)) {
        return;
    }
    const HANDLE mapping = ::CreateFileMappingW(handle, nullptr, PAGE_READONLY, 0, 0, nullptr);
    if (mapping == nullptr) {
        return;
    }
    const auto size = static_cast<std::size_t>(length.QuadPart);
    view_ = ::MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, size);
    ::CloseHandle(mapping);
    if (view_ != nullptr) {
        size_ = size;
    }
#elif defined(__unix__) || defined(__APPLE__)
    const int fd = ::fileno(file);
    struct stat info;
    if (::fstat(fd, &info) != 0 || !S_ISREG(info.st_mode)
        || info.st_size <= 0 || !addressable(info.st_size)) {
        return;
    }
    const auto size = static_cast<std::size_t>(info.st_size);
    void* view = ::mmap(nullptr, size, PROT_READ, MAP_PRIVATE, fd, 0);
    if (view != MAP_FAILED) {
        view_ = view;
        size_ = size;
    }
#else
    (void)file;
#endif
}

SpkFileMapping::~SpkFileMapping() {
#ifdef _WIN32
    if (view_ != nullptr) {
        ::UnmapViewOfFile(view_);
    }
#elif defined(__unix__) || defined(__APPLE__)
    if (size_ != 0) {
        ::munmap(view_, size_);
    }
#endif
}

} // namespace native
} // namespace moira
