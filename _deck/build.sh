#!/bin/sh
# 원본에서 최종본까지 한 번에. 중간 상태를 손으로 만들지 않는다 —
# 두 번 돌리면 슬라이드가 두 장 늘어나는 종류의 사고를 막는다.
set -e
SK="/Users/ks922323/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/f4d8fb0d-a85d-4fc4-b643-3361bb93643e/850c8cd2-d857-449f-8dba-59ff2de1c946/skills/pptx"
rm -rf base
python3 -c "import zipfile;zipfile.ZipFile('base.pptx').extractall('base')"
PYTHONPATH="$SK/scripts" python3 "$SK/scripts/add_slide.py" base/ slide13.xml --after slide13.xml
python3 mknotes15.py
python3 notes.py
python3 patch.py "$@"
python3 "$SK/scripts/office/validate.py" 창업-06-전전컴_최종.pptx --original base.pptx
