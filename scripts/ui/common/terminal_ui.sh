#!/bin/bash

if [ -t 1 ]; then
    BOLD="$(printf '\033[1m')"
    DIM="$(printf '\033[2m')"
    GREEN="$(printf '\033[32m')"
    YELLOW="$(printf '\033[33m')"
    BLUE="$(printf '\033[34m')"
    RED="$(printf '\033[31m')"
    RESET="$(printf '\033[0m')"
else
    BOLD=""
    DIM=""
    GREEN=""
    YELLOW=""
    BLUE=""
    RED=""
    RESET=""
fi

clear_screen() {
    if command -v clear >/dev/null 2>&1; then
        clear
    else
        printf '\033[2J\033[H'
    fi
}

info() {
    printf '%s\n' "${GREEN}==>${RESET} $*"
}

warn() {
    printf '%s\n' "${YELLOW}Warning:${RESET} $*"
}

error() {
    printf '%s\n' "${RED}Error:${RESET} $*" >&2
}

prompt_text() {
    local title="$1"
    local var_name="$2"
    local label="$3"
    local default_value="$4"
    local required="${5:-false}"
    local value
    local current_value="${!var_name:-${default_value}}"

    if [ ! -t 0 ]; then
        if [ "${required}" = "true" ] && [ -z "${current_value}" ]; then
            error "${var_name} is required in non-interactive mode."
            exit 1
        fi
        printf -v "${var_name}" '%s' "${current_value}"
        return
    fi

    while true; do
        clear_screen
        print_header
        printf '%s\n' "${BOLD}${title}${RESET}"
        printf '%s\n\n' "${DIM}Press Enter to accept the value in brackets.${RESET}"
        read -r -p "${label} [${current_value}]: " value
        value="${value:-${current_value}}"

        if [ "${required}" = "true" ] && [ -z "${value}" ]; then
            warn "This value is required."
            read -r -p "Press Enter to try again..." _
            continue
        fi

        printf -v "${var_name}" '%s' "${value}"
        break
    done
}

selected_menu_index=0

select_menu() {
    local title="$1"
    shift
    local options=("$@")
    local selected=0
    local key
    local rest
    local index

    while true; do
        clear_screen
        print_header
        printf '%s\n' "${BOLD}${title}${RESET}"
        printf '%s\n\n' "${DIM}Use arrow keys to move, then press Enter.${RESET}"

        for index in "${!options[@]}"; do
            if [ "${index}" -eq "${selected}" ]; then
                printf '  %s> %s%s\n' "${BLUE}${BOLD}" "${options[${index}]}" "${RESET}"
            else
                printf '    %s\n' "${options[${index}]}"
            fi
        done

        IFS= read -rsn1 key || true
        case "${key}" in
            "")
                selected_menu_index="${selected}"
                return
                ;;
            $'\x1b')
                IFS= read -rsn2 -t 1 rest || true
                case "${rest}" in
                    "[A" | "OA")
                        if [ "${selected}" -le 0 ]; then
                            selected=$((${#options[@]} - 1))
                        else
                            selected=$((selected - 1))
                        fi
                        ;;
                    "[B" | "OB")
                        selected=$(((selected + 1) % ${#options[@]}))
                        ;;
                esac
                ;;
            q | Q)
                selected_menu_index="$((${#options[@]} - 1))"
                return
                ;;
        esac
    done
}
