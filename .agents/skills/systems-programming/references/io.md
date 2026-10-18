# Partial I/O and resource lifetime

## Blocking write loop

Original POSIX C example, for a blocking descriptor and a buffer length that fits
within the platform's permitted write sizes:

```c
#include <errno.h>
#include <stddef.h>
#include <unistd.h>

int write_all_blocking(int fd, const unsigned char *buf, size_t len) {
    size_t done = 0;
    while (done < len) {
        ssize_t n = write(fd, buf + done, len - done);
        if (n > 0) { done += (size_t)n; continue; }
        if (n < 0 && errno == EINTR) continue;
        if (n == 0) errno = EIO;  /* no progress; do not loop forever */
        return -1;
    }
    return 0;
}
```

The buffer must remain valid. This reports failure after a partial transfer
without rolling bytes back. A production interface may need to return progress
so the caller can recover correctly. Very large buffers need chunking to respect
`SSIZE_MAX` and implementation transfer limits. Sockets/pipes may raise `SIGPIPE`
when the peer is gone; choose a deliberate platform-supported handling policy.

On a nonblocking descriptor, `EAGAIN`/`EWOULDBLOCK` is not a reason to busy-loop.
Retain the current offset, await readiness, and honor cancellation/deadlines.
Readiness can become stale before the call; handle the result again. A peer can
close after readiness notification.

## Reading and framing

A stream has bytes, not application message boundaries. One `read` may return half
a header, several messages, or EOF. Keep parser state across reads and enforce
maximum frame size before allocation. A positive short read is not EOF. A zero
return for a positive-length request indicates EOF for normal stream/file cases;
zero-length reads have different significance. Interruption and nonblocking
results require their own policy.

EOF after half a framed message is truncation, even if every `read` succeeded.
Do not treat it as a valid short record unless the application protocol allows it.
Test split headers, split bodies, combined frames, malformed lengths, peer close,
and cancellation during a partial send.

## File descriptors and durability

A descriptor is a small process-local handle; after `close`, its numeric value
can be reused for another resource. Prevent late callbacks from acting on a reused
number through explicit ownership/lifetime control. After `fork`, inherited
handles can keep a pipe/socket alive unexpectedly. Set close-on-exec intentionally
and close unused ends in both parent and child.

A successful `write` is not equivalent to durable storage. Buffered layers and
filesystem/device contracts matter. Use the documented synchronization protocol
when durability is required; syncing the wrong file or ignoring errors leaves
gaps. Atomic replacement involving a directory also needs the platform's documented
rename and directory synchronization assumptions. Do not extrapolate from a clean
process exit to power-loss safety.
