export const TAPTOT_INTRO_SEEN_KEY = "taptot_intro_dismissed";

/** Runs before paint so the homepage hero stays hidden until the intro starts. */
export const TAPTOT_INTRO_BOOT_SCRIPT = `try{if(!window.matchMedia("(prefers-reduced-motion: reduce)").matches&&(new URLSearchParams(location.search).has("intro")||localStorage.getItem("${TAPTOT_INTRO_SEEN_KEY}")!=="1"))document.documentElement.classList.add("tt-intro-active")}catch(e){}`;
