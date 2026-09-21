"""Static tables for familiarization curricula."""

FAMILIARIZATION_WEEKS = 8
FIRST_PUSH_PULL_DAYS = 60
FIRST_PUSH_PULL_WEEKS = 9
FIRST_PUSH_PULL_SESSIONS_PER_WEEK = 3
FIRST_PUSH_PULL_INVERTED_ROW_DAY = 15  # tuần 3: inverted row bàn/xà
FIRST_PUSH_PULL_SCAPULAR_DAY = 29  # tuần 5: scapular hang
FIRST_PUSH_PULL_EARLY_BAR_DAY = FIRST_PUSH_PULL_INVERTED_ROW_DAY
FIRST_PUSH_PULL_BAR_START_DAY = FIRST_PUSH_PULL_SCAPULAR_DAY
MARKER_PREFIX = "seed:familiarization:"

_WEEK_LOAD = {
    1: (2, -2, 4, "Làm quen kỹ thuật"),
    2: (3, -1, 3, "Tích lũy số lần"),
    3: (3, 1, 2, "Tăng dần khối lượng"),
    4: (2, -2, 4, "Giảm tải và kiểm tra giữa kỳ"),
    5: (3, -2, 3, "Biến thể mới"),
    6: (3, 0, 3, "Củng cố"),
    7: (4, 1, 2, "Tuần cao điểm"),
    8: (2, -2, 4, "Giảm tải và kiểm tra cuối kỳ"),
}

_WEEK_ADVANCE = {1: 0, 2: 0, 3: 1, 4: 1, 5: 2, 6: 3, 7: 4, 8: 6}
_PATH_CAPS = {
    "first_push_pull": {"push": 5, "pull": 6, "squat": 1, "plank": 1, "run": 1},
    "basic_foundation": {"push": 5, "pull": 6, "squat": 1, "plank": 1, "run": 1},
    "advanced_foundation": {"push": 6, "pull": 6, "squat": 1, "plank": 1, "run": 1},
}

_WEEKDAY_VI = {
    1: "Thứ 2",
    2: "Thứ 3",
    3: "Thứ 4",
    4: "Thứ 5",
    5: "Thứ 6",
    6: "Thứ 7",
    7: "Chủ nhật",
}

_EXCLUDE_NEEDLES = (
    "ring",
    "vong",
    "machine",
    "lat pull",
    "pulldown",
    "dumbbell",
    "ta tay",
    "kettle",
    "ta chuong",
    "barbell",
    "ta don",
    "cable",
    "cap ",
    "smith",
)
