#include "interpolation_simd.hpp"

#if defined(_MSC_VER) && (defined(_M_X64) || defined(_M_IX86))
#include <intrin.h>
#elif (defined(__GNUC__) || defined(__clang__)) && (defined(__x86_64__) || defined(__i386__))
#include <cpuid.h>
#endif

namespace moira {
namespace native {

bool runtime_avx2_available() noexcept {
#if !defined(MOIRA_NATIVE_AVX2_COMPILED)
    return false;
#elif defined(_MSC_VER) && (defined(_M_X64) || defined(_M_IX86))
    int registers[4] = {0, 0, 0, 0};
    __cpuid(registers, 0);
    if (registers[0] < 7) return false;
    __cpuidex(registers, 1, 0);
    constexpr int osxsave_bit = 1 << 27;
    constexpr int avx_bit = 1 << 28;
    if ((registers[2] & (osxsave_bit | avx_bit)) != (osxsave_bit | avx_bit)) return false;
    if ((_xgetbv(0) & 0x6) != 0x6) return false;
    __cpuidex(registers, 7, 0);
    return (registers[1] & (1 << 5)) != 0;
#elif (defined(__GNUC__) || defined(__clang__)) && (defined(__x86_64__) || defined(__i386__))
    __builtin_cpu_init();
    return __builtin_cpu_supports("avx2");
#else
    return false;
#endif
}

}  // namespace native
}  // namespace moira
