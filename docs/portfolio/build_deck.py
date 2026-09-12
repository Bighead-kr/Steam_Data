"""Fill the 미리캔버스 portfolio template with the real content.

Re-runnable: it always starts from the untouched template and writes a new
file, so correcting a number here and re-running is cheaper than editing
sixteen slides by hand. Anything still unknown is written as a ⟨...⟩
placeholder so it shows up rather than quietly reading as fact.

    python docs/portfolio/build_deck.py
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

BASE = Path(__file__).resolve().parent
# The 6MB template is not committed, so a worktree checkout of this script
# won't have it sitting next to itself - fall back to the main checkout.
MAIN_CHECKOUT = Path("/Users/jung/Desktop/Develop/Data3/docs/portfolio")
TEMPLATE = BASE / "포트폴리오.pptx"
if not TEMPLATE.exists():
    TEMPLATE = MAIN_CHECKOUT / "포트폴리오.pptx"
OUTPUT = TEMPLATE.parent / "데이터분석_포트폴리오_정연웅.pptx"

# This repository is public, so the phone number and email live in an
# untracked file next to this script rather than in the source. See
# profile.local.example.json for the shape.
PROFILE_PATH = BASE / "profile.local.json"

STEAM_SITE = "steam-hidden-gems-web-three.vercel.app"

TABLEAU = "public.tableau.com/app/profile/.18082116/viz/GA4_17884980209280/1_1"
APP_STORE = "apps.apple.com/kr/app/id6790361582"
GOOGLE_PLAY = "play.google.com/store/apps/details?id=com.depaier.clickday"

COUNCIL_TERM = "2025.03 - 2026.02"
CLICKDAY_TERM = "2026.03 - 2026.08"
GA4_TERM = "2026.08 - 2026.09"
STEAM_TERM = "2026.09 - 현재"

# Filled from profile.local.json by build().
P: dict = {}


def load_profile() -> dict:
    if not PROFILE_PATH.exists():
        sys.exit(
            f"missing {PROFILE_PATH}\n"
            "Copy profile.local.example.json to profile.local.json and fill it in."
        )
    return json.loads(PROFILE_PATH.read_text())


# --------------------------------------------------------------------------
# template editing helpers (see the module docstring in pptx_tools for why)
# --------------------------------------------------------------------------
def set_lines(shape, lines: list[str]) -> None:
    """Replace a text box's paragraphs, keeping run-level formatting."""
    tf = shape.text_frame
    while len(tf.paragraphs) < len(lines):
        tf._txBody.append(copy.deepcopy(tf.paragraphs[-1]._p))

    for i, line in enumerate(lines):
        para = tf.paragraphs[i]
        runs = para.runs
        if not runs:
            donor = next((p for p in tf.paragraphs if p.runs), None)
            if donor is None:
                continue
            para._p.append(copy.deepcopy(donor.runs[0]._r))
            runs = para.runs
        runs[0].text = line
        for extra in runs[1:]:
            extra._r.getparent().remove(extra._r)

    for surplus in list(tf.paragraphs)[len(lines) :]:
        surplus._p.getparent().remove(surplus._p)


def duplicate_slide(prs, index: int):
    """Append a copy of slide `index`, pictures included."""
    source = prs.slides[index]
    dest = prs.slides.add_slide(source.slide_layout)
    for shape in list(dest.shapes):
        shape._element.getparent().remove(shape._element)
    for shape in source.shapes:
        dest.shapes._spTree.append(copy.deepcopy(shape._element))
    for rel in source.part.rels.values():
        if "notesSlide" in rel.reltype:
            continue
        if rel.is_external:
            dest.part.rels.get_or_add_ext_rel(rel.reltype, rel.target_ref)
        else:
            dest.part.rels.get_or_add(rel.reltype, rel.target_part)
    return dest


def reorder_slides(prs, order: list[int]) -> None:
    id_list = prs.slides._sldIdLst
    entries = list(id_list)
    for entry in entries:
        id_list.remove(entry)
    for idx in order:
        id_list.append(entries[idx])


def by_name(slide) -> dict:
    return {sh.name: sh for sh in slide.shapes}


def fit_big_number(shape, text: str) -> None:
    """Write the headline figure and shrink it to fit its box.

    The template sized this box for two digits at 196pt, so anything longer
    runs off the slide - which is a bad reason to round 18.5 down to 19 on a
    slide whose whole point is that precision was checked. Digits in Poppins
    SemiBold run about 0.55em, separators about 0.30em.
    """
    from pptx.util import Pt

    box_inches = 4.9
    width_em = sum(0.30 if ch in ".," else 0.55 for ch in text)
    size = min(196, int(72 * box_inches / width_em)) if width_em else 196
    set_lines(shape, [text])
    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            run.font.size = Pt(size)


def clone_row(slide, label_shape, value_shape, dy_inches: float, label: str, value: str) -> None:
    """Add one more row to a label/value list by copying an existing row and
    dropping it `dy_inches` lower. The template's rows are individual text
    boxes, so a list only has as many rows as the designer drew."""
    dy = int(dy_inches * 914400)
    for source, text in ((label_shape, label), (value_shape, value)):
        element = copy.deepcopy(source._element)
        slide.shapes._spTree.append(element)
        clone = slide.shapes[-1]
        clone.top = source.top + dy
        set_lines(clone, [text])


def relax_tracking(slide, max_pt: float = 24.0) -> None:
    """Undo the template's negative letter-spacing on body text.

    The 미리캔버스 export tightens nearly every run - spc="-200" (-2pt) on
    111 of them, "-100" on another 103 - which at 17pt Korean body copy is
    over 12% tighter than the font intends and reads as cramped. Display
    type keeps its tracking: the huge Poppins headings are drawn to sit
    tight, and loosening those would break the look.
    """
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                size_pt = run.font.size.pt if run.font.size else 14
                if size_pt > max_pt:
                    continue
                rPr = run._r.get_or_add_rPr()
                if int(rPr.get("spc", "0")) < 0:
                    rPr.set("spc", "0")


def set_qr(slide, shape_name: str, url: str) -> None:
    """Replace the template's placeholder QR with one that resolves.

    The shipped image is 67x66 px for a 0.69in box - too coarse to scan at
    any size, and it points wherever the template designer pointed it.
    """
    import io

    import qrcode

    target = next((sh for sh in slide.shapes if sh.name == shape_name), None)
    if target is None:
        return
    left, top, width, height = target.left, target.top, target.width, target.height
    target._element.getparent().remove(target._element)

    qr = qrcode.QRCode(box_size=12, border=2)
    qr.add_data(url if url.startswith("http") else f"https://{url}")
    qr.make(fit=True)
    buffer = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    buffer.seek(0)
    slide.shapes.add_picture(buffer, left, top, width, height)


def stamp_header(slide) -> dict:
    """Every slide carries the template's '2099 / Portfolio / @mirikim' strip."""
    shapes = by_name(slide)
    for sh in slide.shapes:
        if not sh.has_text_frame:
            continue
        text = sh.text_frame.text.strip()
        if text == "2099":
            set_lines(sh, ["2026"])
        elif text == "@mirikim":
            # 1.92in box at 14pt: the full github.com/... URL measures about
            # 2.04in and wraps onto a second line across every slide. The
            # template's own '@mirikim' is the size this slot was drawn for.
            set_lines(sh, [P["github_handle"]])
    return shapes


# --------------------------------------------------------------------------
def build() -> None:
    global P
    P = load_profile()
    prs = Presentation(TEMPLATE)

    # ---- project slides are cloned before anything is edited, so each copy
    # ---- starts from the pristine template rather than the previous edit
    ga4_cover, steam_cover, clickday_cover = (duplicate_slide(prs, 5) for _ in range(3))
    ga4_result_1, ga4_result_2, steam_result = (duplicate_slide(prs, 6) for _ in range(3))
    # The AI slide is redrawn from the result slide's parts - see ai_usage().
    ai_usage_slide = duplicate_slide(prs, 6)

    cover(prs.slides[0])
    index(prs.slides[1])
    profile(prs.slides[2])
    introduction(prs.slides[3])
    abilities(prs.slides[4])
    ai_usage(ai_usage_slide)

    project_ga4(ga4_cover)
    project_steam(steam_cover)
    project_clickday(clickday_cover)
    result_ga4_finding(ga4_result_1)
    result_ga4_quality(ga4_result_2)
    result_steam(steam_result)

    closing(prs.slides[7])
    contact(prs.slides[8])

    # Each project cover carries a QR next to its Link row; point it at the
    # thing a reader would most want to open on their phone.
    set_qr(ga4_cover, "Picture 9", TABLEAU)
    set_qr(steam_cover, "Picture 9", STEAM_SITE)
    set_qr(clickday_cover, "Picture 9", APP_STORE)

    for slide in prs.slides:
        relax_tracking(slide)

    # template order: 0 cover, 1 index, 2 profile, 3 intro, 4 abilities,
    # 5 project-cover(original), 6 result(original), 7 closing, 8 contact,
    # then the six project clones at 9..14 and the AI slide at 15.
    # The AI slide sits after Abilities: tools, then how the work using them
    # was actually checked, then the projects that came out of it.
    reorder_slides(prs, [0, 1, 2, 3, 4, 15, 9, 12, 13, 10, 14, 11, 7, 8])

    prs.save(OUTPUT)
    print(f"wrote {OUTPUT}  ({len(prs.slides)} slides)")


# --------------------------------------------------------------------------
def cover(slide) -> None:
    shapes = by_name(slide)
    # The template ships with 'Anaylze' misspelled on the cover.
    set_lines(shapes["TextBox 5"], ["Analyze"])
    set_lines(shapes["TextBox 8"], ["2026"])
    set_lines(shapes["TextBox 3"], ["데이터 분석", "포트폴리오"])
    set_lines(shapes["TextBox 2"], [P["name"], P["phone_spaced"], P["email"]])


def index(slide) -> None:
    shapes = stamp_header(slide)
    set_lines(shapes["TextBox 15"], ["Profile"])
    set_lines(shapes["TextBox 16"], ["이력 · 자격"])
    set_lines(shapes["TextBox 12"], ["Introduction"])
    set_lines(shapes["TextBox 13"], ["일하는 방식"])
    set_lines(shapes["TextBox 9"], ["Abilities"])
    set_lines(shapes["TextBox 10"], ["기술 스택"])
    set_lines(shapes["TextBox 6"], ["Projects"])
    set_lines(shapes["TextBox 7"], ["프로젝트 3건"])


def profile(slide) -> None:
    shapes = stamp_header(slide)
    set_lines(shapes["TextBox 34"], [P["education"]])
    # MBTI earns no space on an analyst's profile; GitHub does.
    set_lines(shapes["TextBox 35"], ["GitHub"])
    set_lines(shapes["TextBox 36"], [P["github"]])

    # No certification to list - the SQLD attempt did not pass - so the
    # section carries the student-council year instead of an empty
    # 'Certification' header. It is the one line of evidence that this
    # candidate has worked alongside other people; there is no internship to
    # point at. It stays a single row here, the story belongs in the cover
    # letter. SQL competence is argued by the query work in the projects.
    set_lines(shapes["TextBox 20"], ["Activity"])
    set_lines(shapes["TextBox 21"], ["Period"])
    set_lines(shapes["TextBox 22"], [f"{COUNCIL_TERM}   한서대학교 항공컴퓨터학과 학회장"])

    # 'Career' has nothing to hold for a new graduate, so the same timeline
    # carries the projects. TextBox 16 is the narrow left-hand label (1.26in
    # wide); the three wide boxes beside it are 17/18/19 - putting a full
    # line in 16 overflowed it and left the word 'Period' sitting where the
    # third project should have been.
    set_lines(shapes["TextBox 15"], ["Experience"])
    set_lines(shapes["TextBox 16"], ["Period"])
    # Oldest first, so the reader walks the same path the candidate did:
    # ship an app, discover nobody arrives, go study acquisition.
    set_lines(shapes["TextBox 17"], [f"{CLICKDAY_TERM}   ClickDay 사진 스팟 공유 앱 (iOS · Android 출시)"])
    set_lines(shapes["TextBox 18"], [f"{GA4_TERM}   GA4 유입채널 성과 분석"])
    set_lines(shapes["TextBox 19"], [f"{STEAM_TERM}        Steam 저평가 게임 발굴 웹앱"])


def introduction(slide) -> None:
    shapes = stamp_header(slide)
    set_lines(
        shapes["TextBox 18"],
        [
            "실데이터를 끝까지 밀어붙이는 과정에서 가설이 틀렸음을 인정하고 결론을 바꾼 경험,",
            "그리고 지표가 튈 때 효과보다 측정 오류를 먼저 의심하는 습관을 갖고 있습니다.",
        ],
    )

    set_lines(shapes["TextBox 15"], ["01 가설을 부정당했을 때"])
    set_lines(
        shapes["TextBox 14"],
        [
            "GA4 분석 중 유료 채널이 하나뿐임을 확인하고,",
            "'예산 재배분'이라는 원래 목표가 이 데이터로는",
            "성립하지 않는다고 판단해 질문을 다시 정의했습니다.",
            "#가설검증",
        ],
    )

    set_lines(shapes["TextBox 12"], ["02 숫자를 믿기 전에 의심하기"])
    set_lines(
        shapes["TextBox 11"],
        [
            "구매 기록 15.9%에 거래ID가 없고 유입 18.5%가",
            "미식별임을 역추적해, 튀는 지표를 '효과'로 읽지 않고",
            "측정 오류를 먼저 확인했습니다.",
            "#데이터품질",
        ],
    )

    set_lines(shapes["TextBox 9"], ["03 배포한 뒤에 다시 검증하기"])
    set_lines(
        shapes["TextBox 8"],
        [
            "테스트 127개가 전부 통과하는 상태에서도 실데이터로",
            "재점검해 죽어 있던 기능 3건을 찾아냈습니다.",
            "테스트 통과와 동작은 다른 문제였습니다.",
            "#실데이터검증",
        ],
    )


def abilities(slide) -> None:
    shapes = stamp_header(slide)
    set_lines(
        shapes["TextBox 32"],
        [
            "SQL로 분석하고, 파이썬으로 수집·적재를 자동화하며,",
            "분석 결과를 대시보드와 웹앱으로 내보내는 것까지 혼자 수행합니다.",
            "",
        ],
    )

    for name, label in (
        ("TextBox 40", "SQL"),
        ("TextBox 46", "분석"),
        ("TextBox 43", "시각화"),
        ("TextBox 49", "파이프라인"),
        ("TextBox 52", "웹 개발"),
    ):
        set_lines(shapes[name], [label])

    for tile, label in (
        ("TextBox 23", "BQ"),
        ("TextBox 21", "Tb"),
        ("TextBox 19", "Py"),
        ("TextBox 17", "Pg"),
        ("TextBox 13", "Fa"),
        ("TextBox 15", "Ne"),
    ):
        set_lines(shapes[tile], [label])
    for caption, label in (
        ("TextBox 24", "BigQuery"),
        ("TextBox 22", "Tableau"),
        ("TextBox 20", "Python"),
        ("TextBox 18", "PostgreSQL"),
        ("TextBox 14", "FastAPI"),
        ("TextBox 16", "Next.js"),
    ):
        set_lines(shapes[caption], [label])

    for circle, label in (
        ("TextBox 26", "SQL"),
        ("TextBox 27", "통계"),
        ("TextBox 28", "ETL"),
        ("TextBox 29", "시각화"),
    ):
        set_lines(shapes[circle], [label, ""])


# The AI slide's own grid, in inches on the 20.00 x 11.25 canvas. The
# template's margins are 0.93 on the left and 19.07 on the right, and its
# body copy starts at 7.22 - the right-hand column lines up with the intro
# paragraph above it, which is how every other slide in this deck is built.
AI_NUM_LEFT = 0.93
AI_LEFT_COL = 2.00
AI_LEFT_WIDTH = 5.10
AI_RIGHT_COL = 7.60
AI_RIGHT_WIDTH = 11.45
AI_RULES = (5.45, 7.20, 8.95, 10.70)

# (number, what the AI produced, why it was wrong, what checking found, detail, tag)
AI_ROWS = (
    (
        "01",
        "덱 초안의 '결함 7건'",
        "출처를 댈 수 없는 수치 · 포트폴리오 덱",
        "근거를 역추적해 출처가 없음을 확인하고, 실측한 3건으로 정정",
        [
            "생성된 문장에 숫자가 있으면 원본 데이터까지 되짚는 것을 규칙으로 삼았습니다.",
            "#사실검증",
        ],
    ),
    (
        "02",
        "정상 응답만 가정한 수집 코드",
        "문서대로 답한다는 전제 · Steam 파이프라인",
        "실행 로그에서 200 OK + 평문 응답을 발견 — 요청의 약 6%에서 태그 유실",
        [
            "SteamSpy는 과부하를 오류 코드가 아니라 200으로 답합니다. 테스트가 아니라",
            "실제 실행 로그를 봐야 보이는 결함이었습니다.",
            "#실행검증",
        ],
    ),
    # The wrong hypotheses themselves are not written down anywhere, so this
    # row says only what the Notion page records: the first diagnosis did not
    # hold, and the cause that did is named. Inventing the misdiagnosis would
    # put a made-up sentence on the slide that argues against made-up
    # sentences.
    (
        "03",
        "콜드스타트 멈춤의 첫 진단",
        "실제 원인이 아니었음 · ClickDay",
        "제안대로 고쳐도 증상이 남아, 원인을 AuthProvider의 네트워크 대기로 다시 좁힘",
        [
            "세션 복구 후 프로필을 받아올 때까지 화면 전환이 멈춰 있었습니다. 캐시가 있으면",
            "즉시 전환하고 최신 프로필은 백그라운드에서 갱신하도록 바꿔 해결했습니다.",
            "#원인규명",
        ],
    ),
)


def place(slide, donor, *, left, top, width, height, lines=None):
    """Drop a copy of `donor` at a measured position on this slide.

    Everything the design owns - typeface, weight, size, colour, tracking -
    rides along in the copied run properties, so a new layout is a matter of
    choosing which donor to borrow and where to put it. Nothing here sets a
    font, and that is deliberate: hand-picked sizes are what make a slide
    look bolted on.
    """
    element = copy.deepcopy(donor._element)
    slide.shapes._spTree.append(element)
    shape = slide.shapes[-1]
    shape.left, shape.top = Inches(left), Inches(top)
    shape.width, shape.height = Inches(width), Inches(height)
    if lines is not None:
        set_lines(shape, lines)
    return shape


def ai_usage(slide) -> None:
    """Build the AI slide out of the result slide's parts.

    Cloning the Introduction page and swapping its text produced a carbon
    copy - same photographs, same three cards, same 'Intro-duction.' heading
    - which is worse than no slide, because a reader notices the repetition
    before the content. This clones the result page instead (no photographs,
    just hairlines and lime numerals), strips its body, and redraws the area
    as a two-column ledger: what the AI produced on the left, what checking
    it caught on the right. Nothing else in the deck is laid out that way,
    and the layout is the argument - the page is about a contrast.
    """
    donors = by_name(slide)
    title, intro = donors["TextBox 30"], donors["TextBox 29"]
    label, rule = donors["TextBox 21"], donors["Picture 7"]
    accent, strong, light = donors["TextBox 18"], donors["TextBox 14"], donors["TextBox 15"]

    # Strip the body. The header strip is matched by its text rather than by
    # shape name, the same way stamp_header() finds it.
    for shape in list(slide.shapes):
        text = shape.text_frame.text.strip() if shape.has_text_frame else ""
        if text not in ("2099", "Portfolio", "@mirikim"):
            shape._element.getparent().remove(shape._element)

    place(slide, title, left=0.93, top=1.67, width=6.85, height=3.28,
          lines=["AI-", "assisted."])
    place(slide, intro, left=7.22, top=2.32, width=11.92, height=0.75, lines=[
        "포트폴리오의 프로젝트 대부분을 Claude Code와 함께 만들었습니다. 생성은 빠르지만, 검증은 사람이 합니다.",
        "아래 세 건은 산출물을 그대로 받았다면 그대로 남았을 오류입니다. 전부 제가 잡아 고쳤습니다.",
    ])

    place(slide, label, left=AI_LEFT_COL, top=5.02, width=3.00, height=0.40,
          lines=["AI Output"])
    place(slide, label, left=AI_RIGHT_COL, top=5.02, width=4.00, height=0.40,
          lines=["Human Check"])

    for y in AI_RULES:
        place(slide, rule, left=0.93, top=y, width=18.14, height=0.06)

    for (number, produced, why, caught, detail), y in zip(AI_ROWS, AI_RULES):
        place(slide, accent, left=AI_NUM_LEFT, top=y + 0.10, width=1.10, height=0.83,
              lines=[number])
        place(slide, strong, left=AI_LEFT_COL, top=y + 0.22,
              width=AI_LEFT_WIDTH, height=0.42, lines=[produced])
        place(slide, light, left=AI_LEFT_COL, top=y + 0.70,
              width=AI_LEFT_WIDTH, height=0.38, lines=[why])
        place(slide, strong, left=AI_RIGHT_COL, top=y + 0.22,
              width=AI_RIGHT_WIDTH, height=0.42, lines=[caught])
        place(slide, light, left=AI_RIGHT_COL, top=y + 0.70,
              width=AI_RIGHT_WIDTH, height=0.85, lines=detail)

    stamp_header(slide)


# --------------------------------------------------------------------------
def _project_cover(slide, *, keyword, title, date, source, skills, summary, link, blurb):
    shapes = stamp_header(slide)
    set_lines(shapes["TextBox 22"], [keyword])
    set_lines(shapes["TextBox 23"], blurb)
    set_lines(shapes["TextBox 11"], [title])
    set_lines(shapes["TextBox 12"], [date])
    set_lines(shapes["TextBox 17"], ["Data"])
    set_lines(shapes["TextBox 13"], [source])
    set_lines(shapes["TextBox 14"], [skills])
    set_lines(shapes["TextBox 15"], summary)
    # A list, because two store URLs do not fit one 9.97in line at 17pt and
    # there is about an inch of clear space below this row.
    set_lines(shapes["TextBox 20"], link if isinstance(link, list) else [link])


def project_ga4(slide) -> None:
    _project_cover(
        slide,
        keyword="#가설검증",
        blurb=["채널을 바꿀 것인가,", "결제 화면을 고칠 것인가."],
        title="GA4 유입채널 성과 분석",
        date=GA4_TERM,
        source="Google Merchandise Store · BigQuery 공개 GA4 이벤트 로그 (2020.11-2021.01)",
        skills="BigQuery(SQL), Tableau Public",
        summary=[
            "1인 분석 — 지표 정의, SQL 분석, 대시보드 제작, A/B 테스트 설계까지 단독 수행.",
            "채널별 유저 질을 4개 독립 분석으로 교차 검증하고, 채널이 아닌 결제 플로우가",
            "진짜 병목임을 밝혀 개선 실험을 설계했습니다.",
        ],
        link=[TABLEAU, P["github"]],
    )


def project_steam(slide) -> None:
    _project_cover(
        slide,
        keyword="#데이터파이프라인",
        blurb=["수집부터 배포까지", "혼자 끝낸 파이프라인."],
        title="Steam 저평가 게임 발굴 파이프라인 & 웹앱",
        date=STEAM_TERM,
        source="Steam Store appdetails API · SteamSpy (게임 9,748건 수집)",
        skills="Python, PostgreSQL(Supabase), FastAPI, Next.js/TypeScript, GitHub Actions, Render, Vercel",
        summary=[
            "리뷰 품질은 상위권인데 소유자 수는 하위권인 게임을 베이지안 보정 + 코호트",
            "백분위로 점수화해 랭킹으로 보여주는 서비스. 수집·적재·스코어링·API·웹앱·",
            "CI/CD·프로덕션 배포까지 1인 수행.",
        ],
        link=f"{STEAM_SITE} · " + P["github"] + "/Steam_Data",
    )


def project_clickday(slide) -> None:
    _project_cover(
        slide,
        keyword="#출시경험",
        blurb=["만드는 것과 알리는 것은", "다른 문제였습니다."],
        # Named from the store listing, not from memory: it is a photo-spot
        # sharing community (where and with what a shot was taken), not an
        # EXIF viewer.
        title="ClickDay — 사진 스팟 공유 앱",
        date=CLICKDAY_TERM,
        source="개인 프로젝트 · App Store / Google Play 출시 (2026.07)",
        skills="React Native(Expo), TypeScript",
        summary=[
            "사진에 담긴 '어디서, 무엇으로' 찍었는지를 지도 위에 기록하고 공유하는 앱을",
            "기획·개발해 iOS·Android 양대 스토어에 출시했습니다. 홍보를 하지 않아 이용자는",
            "약 30명에 그쳤고, 이 경험이 '유입 채널'을 공부하게 된 직접적인 계기가 됐습니다.",
        ],
        link=[APP_STORE, GOOGLE_PLAY],
    )


# --------------------------------------------------------------------------
def _result(slide, *, keyword, title, date, role, result, top, bottom):
    """`top`/`bottom` are (big number, unit, headline, subhead, [detail...])."""
    shapes = stamp_header(slide)
    set_lines(shapes["TextBox 20"], [keyword])
    set_lines(shapes["TextBox 22"], [title])
    set_lines(shapes["TextBox 23"], [date])
    set_lines(shapes["TextBox 24"], [role])
    set_lines(shapes["TextBox 25"], [result])

    big, unit, headline, subhead, detail = top
    fit_big_number(shapes["TextBox 16"], big)
    set_lines(shapes["TextBox 18"], [unit])
    set_lines(shapes["TextBox 13"], [headline])
    set_lines(shapes["TextBox 14"], [subhead])
    set_lines(shapes["TextBox 15"], detail)

    big, unit, headline, subhead, detail = bottom
    fit_big_number(shapes["TextBox 17"], big)
    set_lines(shapes["TextBox 19"], [unit])
    set_lines(shapes["TextBox 10"], [headline])
    set_lines(shapes["TextBox 11"], [subhead])
    set_lines(shapes["TextBox 12"], detail)

    set_lines(
        shapes["TextBox 29"],
        [
            "숫자는 모두 실제 분석 결과이며, 근거 쿼리는 GitHub에 공개돼 있습니다.",
            "실험 결과처럼 확인할 수 없는 값은 설계까지만 제시하고 지어내지 않았습니다.",
        ],
    )


def result_ga4_finding(slide) -> None:
    _result(
        slide,
        keyword="#핵심결론",
        title="GA4 유입채널 성과 분석",
        date=GA4_TERM,
        role="1인 분석 (SQL · 시각화 · 실험설계)",
        result="채널이 아니라 결제 플로우가 병목",
        # The headline figure has to carry the conclusion. '7배' shouted
        # "huge difference" directly above a headline saying the differences
        # didn't matter - the number was arguing against its own slide.
        # Headline 24pt / subhead 19pt / detail 17pt, all in a ~5.9in column:
        # roughly 16, 20 and 22 Korean characters per line respectively.
        top=(
            "0.1",
            "%p",
            "전환율 차이는 0.1%p뿐이었다",
            "볼륨은 최대 7배 차이인데도",
            [
                "Organic 37.7% vs Paid 5.3% — 볼륨은 최대 7배",
                "전환율 1.52~1.63% · 도달률 21.8~22.8% · 객단가 $46~49",
                "4개 독립 분석 모두 채널 간 차이가 없었습니다.",
            ],
        ),
        bottom=(
            "40.8",
            "%",
            "진짜 병목은 결제정보 입력 구간",
            "전 채널 공통으로 결제 시작 → 정보 입력에서 이탈",
            [
                "9,715명 중 3,964명 — 특정 채널이 아닌 전 채널 공통",
                "A/B 설계: 45.5%→49.5%(MDE +4%p), 4,900명, 7~10주",
            ],
        ),
    )


def result_ga4_quality(slide) -> None:
    _result(
        slide,
        keyword="#데이터품질",
        title="GA4 유입채널 성과 분석",
        date=GA4_TERM,
        role="1인 분석 (SQL · 시각화 · 실험설계)",
        result="지표를 해석하기 전에 측정을 검증",
        top=(
            "15.9",
            "%",
            "거래ID 없는 구매 기록",
            "중복 구매 검증이 불가능한 비율을 먼저 확인",
            [
                "집계에 쓰기 전에 데이터가 무엇을 보장하지 못하는지 명시했습니다.",
            ],
        ),
        bottom=(
            "18.5",
            "%",
            "유입채널 식별 불가",
            "그중 5.5%는 크로스도메인 추적 끊김으로 경로가 유실",
            [
                "지표가 튀는 그룹을 '효과'로 해석하지 않고,",
                "추적 시스템 결함을 역추적해 원인을 특정했습니다.",
            ],
        ),
    )


def result_steam(slide) -> None:
    _result(
        slide,
        keyword="#실데이터검증",
        title="Steam 저평가 게임 발굴 웹앱",
        date=STEAM_TERM,
        role="1인 개발 (ETL · DB · API · 배포)",
        result="재점검으로 죽은 기능 3건 발견",
        # 127 is not the finding, it is the irony's setup - the damage is the
        # figure worth enlarging. Same below: the point is "all of them",
        # which reads as 100%, not as a row count.
        top=(
            "3",
            "건",
            "배포된 사이트에서 죽어 있던 기능",
            "테스트 127개는 그동안 전부 통과하고 있었습니다",
            [
                "원인은 테스트 픽스처가 실제 API 응답보다 관대했던 것 —",
                "외부 API의 실제 응답 형태를 픽스처로 고정해 재발을 막았습니다.",
            ],
        ),
        bottom=(
            "100",
            "%",
            "태그 누락률",
            "9,715건 전부 — 태그 필터가 매칭될 수 없었습니다",
            [
                "코호트 장르도 한쪽으로 쏠렸습니다 (action 4,558건 vs simulation 1건).",
                "장르 기준을 재정의하고 API 쿼리를 SQL로 내렸습니다.",
            ],
        ),
    )


# --------------------------------------------------------------------------
def closing(slide) -> None:
    shapes = stamp_header(slide)
    # The last paragraph deliberately mixes weights (name semibold, the rest
    # light), so its runs are set individually instead of collapsed into one.
    set_lines(
        shapes["TextBox 11"],
        ["감사합니다.", "저는                           한", f"{P['name']}입니다."],
    )
    set_lines(shapes["TextBox 12"], [P["adjective"]])
    set_lines(shapes["TextBox 5"], [P["phone"]])
    set_lines(shapes["TextBox 7"], [P["email"]])
    set_lines(shapes["TextBox 8"], ["GitHub"])
    set_lines(shapes["TextBox 9"], [P["github"]])
    set_lines(shapes["TextBox 6"], ["E.Mail"])
    # The template's own disclaimer about its sample portrait. The portrait
    # itself is still on this slide - replace or delete it in PowerPoint.
    set_lines(shapes["TextBox 10"], ["* 인물 사진은 템플릿 샘플 — 교체 또는 삭제 필요"])


def contact(slide) -> None:
    shapes = stamp_header(slide)
    set_lines(shapes["TextBox 9"], [f"{P['name']}입니다.", "읽어주셔서 감사합니다."])
    set_lines(shapes["TextBox 8"], [P["signature"]])
    set_lines(shapes["TextBox 3"], [P["phone"]])
    set_lines(shapes["TextBox 5"], [P["email"]])
    set_lines(shapes["TextBox 6"], ["GitHub"])
    set_lines(shapes["TextBox 7"], [P["github"]])


if __name__ == "__main__":
    if not TEMPLATE.exists():
        sys.exit(f"template not found: {TEMPLATE}")
    # This script rebuilds all fourteen slides from the template, so running
    # it over a deck that was finished by hand in PowerPoint throws that work
    # away - which is exactly what happened once. Overwriting is now something
    # you have to ask for. To add a slide to a deck you have already edited,
    # use add_ai_slide.py, which writes a new file instead.
    if OUTPUT.exists() and "--force" not in sys.argv:
        sys.exit(
            f"{OUTPUT.name} already exists.\n"
            "Rebuilding replaces every slide and discards any edit made by hand.\n"
            "  --force        rebuild anyway\n"
            "  add_ai_slide.py  add one slide to the existing deck instead"
        )
    build()
