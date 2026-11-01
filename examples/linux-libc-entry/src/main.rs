#![no_std]
#![no_main]

#[cfg(not(all(target_os = "linux", target_env = "gnu", target_arch = "x86_64")))]
compile_error!("This example supports x86_64-unknown-linux-gnu only.");

use core::{arch::naked_asm, panic::PanicInfo};

// The kernel enters _start directly, without a C caller's return address.
// Align before CALL so the Rust body receives a normal SysV call frame.
#[unsafe(naked)]
#[unsafe(no_mangle)]
pub unsafe extern "C" fn _start() -> ! {
    naked_asm!(
        "xor ebp, ebp",
        "and rsp, -16",
        "call {body}",
        "ud2",
        body = sym program,
    );
}

extern "C" fn program() -> ! {
    #[cfg(feature = "panic-probe")]
    panic!("deliberate link-check failure");

    #[cfg(not(feature = "panic-probe"))]
    {
        const MESSAGE: &[u8] = b"Hello from no_std and libc.\n";
        // MESSAGE is static and initialized; write reads exactly its length.
        // Do not depend on stdio buffering or exit handlers with CRT skipped.
        let written =
            unsafe { libc::write(libc::STDOUT_FILENO, MESSAGE.as_ptr().cast(), MESSAGE.len()) };
        let status = if written == MESSAGE.len() as libc::ssize_t {
            0
        } else {
            1
        };
        unsafe { libc::_exit(status) }
    }
}

#[panic_handler]
fn panic_is_not_allowed(_: &PanicInfo<'_>) -> ! {
    unsafe extern "C" {
        fn rust_panic_is_reachable_in_this_build() -> !;
    }
    // The symbol is deliberately undefined. A retained Rust panic path makes
    // this executable fail to link instead of silently becoming panic=abort.
    unsafe { rust_panic_is_reachable_in_this_build() }
}
