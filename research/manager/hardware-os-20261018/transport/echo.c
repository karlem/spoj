#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/tcp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static const size_t sizes[] = {128, 16384, 1048576};
static const unsigned counts[] = {128, 16, 2};
static void die(const char *s) { perror(s); exit(1); }
static uint64_t now_ns(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) die("clock_gettime");
    return (uint64_t)t.tv_sec * UINT64_C(1000000000) + (uint64_t)t.tv_nsec;
}
static int transfer(int fd, unsigned char *buf, size_t n, int sending) {
    size_t off = 0;
    while (off < n) {
        ssize_t k = sending ? send(fd, buf + off, n - off, MSG_NOSIGNAL)
                            : recv(fd, buf + off, n - off, 0);
        if (k < 0 && errno == EINTR) continue;
        if (k <= 0) return -1;
        off += (size_t)k;
    }
    return 0;
}
static void options(int fd, int tcp) {
    struct timeval tv = {5, 0};
    int yes = 1;
    if (setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof tv) ||
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv)) die("timeout");
    if (tcp && setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &yes, sizeof yes)) die("nodelay");
}
static void print_rusage(const char *role, const struct rusage *r) {
    printf("{\"kind\":\"rusage\",\"role\":\"%s\",\"user_us\":%lld,\"system_us\":%lld,\"maxrss_kib\":%ld,\"minor_faults\":%ld,\"major_faults\":%ld,\"voluntary_switches\":%ld,\"involuntary_switches\":%ld}\n",
        role, (long long)r->ru_utime.tv_sec*1000000 + r->ru_utime.tv_usec,
        (long long)r->ru_stime.tv_sec*1000000 + r->ru_stime.tv_usec,
        r->ru_maxrss, r->ru_minflt, r->ru_majflt, r->ru_nvcsw, r->ru_nivcsw);
}
int main(int argc, char **argv) {
    if (argc != 3 || (strcmp(argv[1], "tcp") && strcmp(argv[1], "unix")) ||
        (strcmp(argv[2], "normal") && strcmp(argv[2], "corrupt"))) return 2;
    const int tcp = !strcmp(argv[1], "tcp"), corrupt = !strcmp(argv[2], "corrupt");
    unsigned char *tx = malloc(sizes[2]), *rx = malloc(sizes[2]), *server = malloc(sizes[2]);
    if (!tx || !rx || !server) die("malloc");
    for (size_t j = 0; j < sizes[2]; ++j) tx[j] = (unsigned char)((j*131U + 17U) & 255U);
    memset(rx, 0, sizes[2]); memset(server, 0, sizes[2]);
    uint64_t setup_start = now_ns();
    int listener = socket(tcp ? AF_INET : AF_UNIX, SOCK_STREAM, 0);
    if (listener < 0) die("listener");
    struct sockaddr_storage address;
    memset(&address, 0, sizeof address);
    socklen_t len;
    if (tcp) {
        struct sockaddr_in *a = (struct sockaddr_in *)&address;
        a->sin_family = AF_INET; a->sin_addr.s_addr = htonl(INADDR_LOOPBACK); a->sin_port = 0;
        len = sizeof *a;
    } else {
        struct sockaddr_un *a = (struct sockaddr_un *)&address;
        a->sun_family = AF_UNIX;
        (void)snprintf(a->sun_path + 1, sizeof a->sun_path - 1, "spoj-transport-%ld", (long)getpid());
        len = sizeof *a;
    }
    options(listener, tcp);
    if (bind(listener, (struct sockaddr *)&address, len) || listen(listener, 1)) die("bind/listen");
    if (tcp && getsockname(listener, (struct sockaddr *)&address, &len)) die("getsockname");
    pid_t parent = getpid();
    pid_t child = fork();
    if (child < 0) die("fork");
    if (child == 0) {
        if (prctl(PR_SET_PDEATHSIG, SIGKILL) || getppid() != parent) _exit(3);
        int peer = accept(listener, NULL, NULL);
        if (peer < 0) _exit(4);
        close(listener); options(peer, tcp);
        for (unsigned p = 0; p < (corrupt ? 1U : 3U); ++p) {
            unsigned n = corrupt ? 1U : counts[p] + 2U;
            for (unsigned i = 0; i < n; ++i) {
                if (transfer(peer, server, sizes[p], 0)) _exit(5);
                if (corrupt) server[127] ^= 1U; /* negative mode is exactly 128 bytes */
                if (transfer(peer, server, sizes[p], 1)) _exit(6);
            }
        }
        close(peer); _exit(0);
    }
    int fd = socket(tcp ? AF_INET : AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) die("client socket");
    options(fd, tcp);
    if (connect(fd, (struct sockaddr *)&address, len)) die("connect");
    close(listener);
    uint64_t setup_ns = now_ns() - setup_start;
    int snd = 0, rcv = 0; socklen_t optlen = sizeof snd;
    if (getsockopt(fd, SOL_SOCKET, SO_SNDBUF, &snd, &optlen) ||
        getsockopt(fd, SOL_SOCKET, SO_RCVBUF, &rcv, &optlen)) die("getsockopt");
    printf("{\"kind\":\"setup\",\"transport\":\"%s\",\"setup_ns\":%llu,\"sndbuf\":%d,\"rcvbuf\":%d,\"tcp_nodelay\":%s}\n",
        argv[1], (unsigned long long)setup_ns, snd, rcv, tcp ? "true" : "false");
    int result = 0; uint64_t sequence = 0, bytes = 0; unsigned successful = 0;
    for (unsigned p = 0; p < (corrupt ? 1U : 3U) && !result; ++p) {
        unsigned n = corrupt ? 1U : counts[p] + 2U;
        for (unsigned i = 0; i < n; ++i) {
            ++sequence;
            memcpy(tx, &sequence, sizeof sequence);
            uint64_t t = now_ns();
            int io_ok = !transfer(fd, tx, sizes[p], 1) && !transfer(fd, rx, sizes[p], 0);
            int equal = io_ok && memcmp(tx, rx, sizes[p]) == 0;
            uint64_t dt = now_ns() - t;
            if (io_ok) bytes += 2 * sizes[p];
            if (equal) ++successful;
            printf("{\"kind\":\"request\",\"payload_bytes\":%zu,\"sequence\":%llu,\"warmup\":%s,\"rtt_verify_ns\":%llu,\"io_ok\":%s,\"equal\":%s,\"completed_echo_bytes\":%zu}\n",
                sizes[p], (unsigned long long)sequence, !corrupt && i < 2 ? "true" : "false",
                (unsigned long long)dt, io_ok ? "true" : "false", equal ? "true" : "false",
                io_ok ? 2 * sizes[p] : 0);
            if (!equal) { result = io_ok ? 42 : 7; break; }
        }
    }
    close(fd);
    int status = 0; struct rusage usage;
    if (wait4(child, &status, 0, &usage) != child) die("wait4");
    int child_exit = WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
    print_rusage("server", &usage);
    if (getrusage(RUSAGE_SELF, &usage)) die("getrusage");
    print_rusage("client", &usage);
    if (child_exit && !result) result = 8;
    printf("{\"kind\":\"final\",\"child_exit\":%d,\"exit\":%d,\"successful_requests\":%u,\"completed_echo_bytes\":%llu}\n",
        child_exit, result, successful, (unsigned long long)bytes);
    free(tx); free(rx); free(server);
    return result;
}
