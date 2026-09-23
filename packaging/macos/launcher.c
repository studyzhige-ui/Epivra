#include <mach-o/dyld.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    char executable[PATH_MAX], resolved[PATH_MAX], python[PATH_MAX];
    uint32_t size = sizeof(executable);
    if (_NSGetExecutablePath(executable, &size) != 0 ||
        !realpath(executable, resolved)) return 1;
    char *slash = strrchr(resolved, '/');
    if (!slash) return 1;
    *slash = '\0';
    if (snprintf(python, sizeof(python), "%s/../Resources/runtime/bin/python3", resolved) >= sizeof(python)) return 1;
    char **arguments = calloc((size_t)argc + 4, sizeof(char *));
    if (!arguments) return 1;
    arguments[0] = python;
    arguments[1] = "-I";
    arguments[2] = "-m";
    arguments[3] = "epivra.desktop";
    for (int i = 1; i < argc; i++) arguments[i + 3] = argv[i];
    execv(python, arguments);
    perror("Epivra");
    return 1;
}
