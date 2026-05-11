#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LCARS Command Console v2 — Claude Code Statusline
# 3-panel display · gradient spectrum · thermal rate gauge
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

input=$(cat)

# ── Extract telemetry ──
eval $(echo "$input" | jq -r '
  @sh "MODEL=\(.model.display_name)",
  @sh "DIR=\(.workspace.current_dir)",
  @sh "COST=\(.cost.total_cost_usd // 0)",
  @sh "PCT=\(.context_window.used_percentage // 0)",
  @sh "DURATION_MS=\(.cost.total_duration_ms // 0)",
  @sh "LINES_ADD=\(.cost.total_lines_added // 0)",
  @sh "LINES_DEL=\(.cost.total_lines_removed // 0)",
  @sh "VIM_MODE=\(.vim.mode // "")",
  @sh "CTX_SIZE=\(.context_window.context_window_size // 200000)",
  @sh "CUR_INPUT=\(.context_window.current_usage.input_tokens // 0)",
  @sh "CUR_OUTPUT=\(.context_window.current_usage.output_tokens // 0)",
  @sh "CACHE_CREATE=\(.context_window.current_usage.cache_creation_input_tokens // 0)",
  @sh "CACHE_READ=\(.context_window.current_usage.cache_read_input_tokens // 0)",
  @sh "RL_5H=\(.rate_limits.five_hour.used_percentage // -1)",
  @sh "RL_5H_RESET=\(.rate_limits.five_hour.resets_at // "")",
  @sh "RL_7D=\(.rate_limits.seven_day.used_percentage // -1)",
  @sh "RL_7D_RESET=\(.rate_limits.seven_day.resets_at // "")",
  @sh "EFFORT=\(.effort.level // "")"
' | tr ',' '\n')
PCT=$(echo "$PCT" | cut -d. -f1)

# ── Primitives ──
RST='\033[0m'; BD='\033[1m'; DM='\033[2m'
fg() { printf '\033[38;2;%d;%d;%dm' "$1" "$2" "$3"; }

# ── LCARS Palette ──
AMBER=$(fg 255 153 0);    GOLD=$(fg 255 204 51);   PEACH=$(fg 255 180 130)
TEAL=$(fg 0 204 204);     ICE=$(fg 140 200 255);    LAVENDER=$(fg 170 150 255)
LIME=$(fg 80 240 130);    CORAL=$(fg 255 90 90);    TANGERINE=$(fg 255 140 50)
SLATE=$(fg 100 110 130);  GHOST=$(fg 60 65 80)

# ── Git (cached 5s) ──
_PFX="${TMPDIR:-/tmp}/claude-sl"
_GC="${_PFX}-git"; _DC="${_PFX}-dir"
_PD=""; [ -f "$_DC" ] && _PD=$(cat "$_DC")
if [ "$DIR" != "$_PD" ] || [ ! -f "$_GC" ] || \
   [ $(($(date +%s) - $(stat -f %m "$_GC" 2>/dev/null || echo 0))) -gt 5 ]; then
    echo "$DIR" > "$_DC"
    if git -C "$DIR" rev-parse --git-dir >/dev/null 2>&1; then
        echo "$(git -C "$DIR" branch --show-current 2>/dev/null)|\
$(git -C "$DIR" diff --cached --numstat 2>/dev/null | wc -l | tr -d ' ')|\
$(git -C "$DIR" diff --numstat 2>/dev/null | wc -l | tr -d ' ')|\
$(git -C "$DIR" remote get-url origin 2>/dev/null \
    | sed 's/git@github\.com:/https:\/\/github.com\//' \
    | sed 's/git@bitbucket\.org:/https:\/\/bitbucket.org\//' \
    | sed 's/\.git$//')|\
$(( $(date +%s) - $(git -C "$DIR" --no-optional-locks log -1 --format=%ct 2>/dev/null || echo 0) ))" > "$_GC"
    else
        echo "||||0" > "$_GC"
    fi
fi
IFS='|' read -r BRANCH STAGED MODIFIED REMOTE COMMIT_AGE < "$_GC"

# ── Token format ──
tf() {
    local t=$1
    if [ "$t" -ge 1000000 ] 2>/dev/null; then printf '%.1fM' "$(echo "$t/1000000" | bc -l)"
    elif [ "$t" -ge 1000 ] 2>/dev/null; then printf '%.0fk' "$(echo "$t/1000" | bc -l)"
    else printf '%d' "$t"; fi
}

# ━━━ Computed values ━━━
USED=$((CUR_INPUT + CACHE_CREATE + CACHE_READ))
US=$(tf "$USED"); SS=$(tf "$CTX_SIZE"); IS=$(tf "$CUR_INPUT"); OS=$(tf "$CUR_OUTPUT")
CH=0; TC=$((CACHE_CREATE + CACHE_READ))
[ "$TC" -gt 0 ] 2>/dev/null && CH=$((CACHE_READ * 100 / TC))
CS=$(printf '$%.2f' "$COST")
M=$((DURATION_MS / 60000)); S=$(((DURATION_MS % 60000) / 1000))
if [ "$M" -ge 1440 ]; then DS="$((M/1440))d$((M%1440/60))h"
elif [ "$M" -ge 60 ]; then DS="$((M/60))h$((M%60))m"
else DS="${M}m${S}s"; fi

# Context health → color (used for CTX pill + percentage)
if   [ "$PCT" -ge 90 ]; then CR=255; CG=90;  CB=90
elif [ "$PCT" -ge 70 ]; then CR=255; CG=153; CB=0
elif [ "$PCT" -ge 50 ]; then CR=255; CG=204; CB=51
else                          CR=0;   CG=204; CB=204; fi

# ━━━ Context spectrum bar ━━━
# 20-segment gradient: teal(0,204,204)→lime→gold→tangerine→coral(255,90,90)
# Filled = █ with per-char interpolated color · Empty = ▒ ghost
BAR=""
for i in $(seq 1 20); do
    p=$((i * 5))
    if [ "$p" -le "$PCT" ]; then
        # 5-stop linear gradient (integer math, no subshells)
        if [ "$p" -le 25 ]; then
            t=$((p * 4)); r=$((80*t/100)); g=$((204+36*t/100)); b=$((204-74*t/100))
        elif [ "$p" -le 50 ]; then
            t=$(((p-25)*4)); r=$((80+175*t/100)); g=$((240-36*t/100)); b=$((130-79*t/100))
        elif [ "$p" -le 75 ]; then
            t=$(((p-50)*4)); r=255; g=$((204-64*t/100)); b=$((51-t/100))
        else
            t=$(((p-75)*4)); r=255; g=$((140-50*t/100)); b=$((50+40*t/100))
        fi
        BAR="${BAR}\033[38;2;${r};${g};${b}m█${RST}"
    else
        BAR="${BAR}\033[38;2;60;65;80m▒${RST}"
    fi
done

# ━━━ Rate limit thermal gauges ━━━
# Rising blocks ▁▃▅▇█ with heat colors per segment; one gauge per window.
# Helper writes to GAUGE/GCOLOR globals (avoids subshells).
_thermal() {
    local pct=$1
    GAUGE=""
    for seg in "0 0 204 204 ▁" "20 80 240 130 ▃" "40 255 204 51 ▅" "60 255 140 50 ▇" "80 255 90 90 █"; do
        read th sr sg sb ch <<< "$seg"
        if [ "$pct" -gt "$th" ] 2>/dev/null; then
            GAUGE="${GAUGE}\033[38;2;${sr};${sg};${sb}m${ch}${RST}"
        else
            GAUGE="${GAUGE}\033[38;2;60;65;80m${ch}${RST}"
        fi
    done
    if   [ "$pct" -ge 90 ]; then GCOLOR="${CORAL}"
    elif [ "$pct" -ge 70 ]; then GCOLOR="${TANGERINE}"
    elif [ "$pct" -ge 50 ]; then GCOLOR="${GOLD}"
    else                          GCOLOR="${SLATE}"; fi
}

# Helper: parse rate-limit reset timestamp (epoch or ISO 8601) → short countdown.
# Writes to COUNTDOWN; empty string when input is missing/expired/unparseable.
_countdown() {
    local raw="$1"
    COUNTDOWN=""
    [ -z "$raw" ] && return
    local ts=""
    if [ "$raw" -gt 0 ] 2>/dev/null; then
        ts="$raw"
    else
        local clean="${raw%%.*}"; clean="${clean%%Z}"; clean="${clean%%+*}"
        ts=$(date -j -u -f "%Y-%m-%dT%H:%M:%S" "$clean" "+%s" 2>/dev/null || \
             date -d "$raw" "+%s" 2>/dev/null)
    fi
    [ -z "$ts" ] && return
    local left=$((ts - $(date +%s)))
    [ "$left" -le 0 ] && return
    if   [ "$left" -ge 86400 ]; then COUNTDOWN="$((left/86400))d$((left%86400/3600))h"
    elif [ "$left" -ge 3600 ];  then COUNTDOWN="$((left/3600))h$((left%3600/60))m"
    elif [ "$left" -ge 60 ];    then COUNTDOWN="$((left/60))m"
    else                              COUNTDOWN="${left}s"; fi
}

RL5=$(echo "$RL_5H" | cut -d. -f1)
RL7=$(echo "$RL_7D" | cut -d. -f1)
RLG=""; RLC=""; RL7G=""; RL7CC=""
if [ "$RL5" -ge 0 ] 2>/dev/null; then
    _thermal "$RL5"; RLG="$GAUGE"; RLC="$GCOLOR"
fi
if [ "$RL7" -ge 0 ] 2>/dev/null; then
    _thermal "$RL7"; RL7G="$GAUGE"; RL7CC="$GCOLOR"
fi

# ━━━ LCARS Pills (inline — zero subshells) ━━━
# ▐ LABEL ▌ with colored background, dark text
_pill() { printf "\033[38;2;${1};${2};${3}m▐\033[48;2;${1};${2};${3}m\033[38;2;12;12;18m${BD} ${4} ${RST}\033[38;2;${1};${2};${3}m▌${RST}"; }
SYS_P=$(_pill 255 153 0 SYS)
CTX_P=$(_pill $CR $CG $CB CTX)
OPS_P=$(_pill 0 204 204 OPS)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LCARS Output — 3-panel display
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── Panel SYS: system + workspace ──
EFFORT_TAG=""
[ -n "$EFFORT" ] && EFFORT_TAG=" ${GHOST}${DM}(${EFFORT})${RST}"
L1="${SYS_P} ${TEAL}${BD}◆ ${MODEL}${RST}${EFFORT_TAG} ${GHOST}░${RST} ${PEACH}${BD}${DIR##*/}${RST}"
if [ -n "$BRANCH" ]; then
    L1="${L1} ${GHOST}░${RST} "
    [ -n "$REMOTE" ] && L1="${L1}\e]8;;${REMOTE}\a${ICE}${REMOTE##*/}\e]8;;\a "
    L1="${L1}${LAVENDER}⎇ ${BRANCH}${RST}"
    [ "$STAGED" -gt 0 ] 2>/dev/null && L1="${L1} ${LIME}●${STAGED} ${RST}${GHOST}staged${RST}"
    [ "$MODIFIED" -gt 0 ] 2>/dev/null && L1="${L1} ${GOLD}◌${MODIFIED} ${RST}${GHOST}mod${RST}"
    if [ "$COMMIT_AGE" -gt 0 ] 2>/dev/null; then
        if   [ "$COMMIT_AGE" -lt 3600 ];   then A="$((COMMIT_AGE/60))m";    AC="${LIME}"
        elif [ "$COMMIT_AGE" -lt 86400 ];  then A="$((COMMIT_AGE/3600))h";  AC="${GOLD}"
        elif [ "$COMMIT_AGE" -lt 604800 ]; then A="$((COMMIT_AGE/86400))d"; AC="${TANGERINE}"
        else                                     A="$((COMMIT_AGE/604800))w"; AC="${CORAL}"; fi
        L1="${L1} ${AC}${DM}◷ ${A} ${RST}${GHOST}ago${RST}"
    fi
fi
[ -n "$VIM_MODE" ] && { [ "$VIM_MODE" = "NORMAL" ] && L1="${L1} ${GHOST}[N]${RST}" || L1="${L1} ${LIME}${BD}[I]${RST}"; }

# ── Panel CTX: context gauge + token I/O ──
PC=$(fg $CR $CG $CB)
L2="${CTX_P} ${BAR} ${PC}${BD}${PCT}%${RST} ${DM}${US}/${SS}${RST} ${GHOST}░${RST} ${GHOST}in ${RST}${ICE}↓${IS}${RST} ${GHOST}out ${RST}${PEACH}↑${OS}${RST}"
[ "$TC" -gt 0 ] 2>/dev/null && L2="${L2} ${GHOST}cache ${RST}${TEAL}⛃${CH}%${RST}"

# ── Panel OPS: cost · time · delta · rate limit ──
L3="${OPS_P} ${GHOST}cost ${RST}${GOLD}${CS}${RST} ${GHOST}░${RST} ${GHOST}active ${RST}${SLATE}${DS}${RST}"
([ "$LINES_ADD" -gt 0 ] 2>/dev/null || [ "$LINES_DEL" -gt 0 ] 2>/dev/null) && \
    L3="${L3} ${GHOST}░${RST} ${GHOST}Δ ${RST}${LIME}+${LINES_ADD}${RST} ${CORAL}-${LINES_DEL}${RST}"
# Render the "usage" block when either window has data.
if [ -n "$RLG" ] || [ -n "$RL7G" ]; then
    L3="${L3} ${GHOST}░ usage${RST}"
    if [ -n "$RLG" ]; then
        L3="${L3} ${RLG} ${RLC}${RL5}%${RST}${GHOST}5h${RST}"
        _countdown "$RL_5H_RESET"
        [ -n "$COUNTDOWN" ] && L3="${L3} ${GHOST}↻${COUNTDOWN}${RST}"
    fi
    if [ -n "$RL7G" ]; then
        # Subtle separator only when both windows render side-by-side
        [ -n "$RLG" ] && L3="${L3} ${GHOST}·${RST}"
        L3="${L3} ${RL7G} ${RL7CC}${RL7}%${RST}${GHOST}7d${RST}"
        _countdown "$RL_7D_RESET"
        [ -n "$COUNTDOWN" ] && L3="${L3} ${GHOST}↻${COUNTDOWN}${RST}"
    fi
fi

# ── Render ──
printf '%b\n' "$L1"
printf '%b\n' "$L2"
printf '%b\n' "$L3"
