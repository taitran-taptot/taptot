import { describe, expect, it } from "vitest";
import { htmlToMarkdown, renderMarkdown } from "./markdown";

describe("renderMarkdown", () => {
  it("renders bold, italic, and bullets", () => {
    const html = renderMarkdown("**Ngực**\n_Lưng_\n- Ngày nghỉ");
    expect(html).toContain("<strong");
    expect(html).toContain("Ngực");
    expect(html).toContain("<em>Lưng</em>");
    expect(html).toContain("<ul");
    expect(html).toContain("<li>");
  });

  it("renders pending image placeholders as dashed frames", () => {
    const html = renderMarkdown("![Bản đồ nhóm cơ](pending:muscle-heat-map)");
    expect(html).toContain('data-pending-image="muscle-heat-map"');
    expect(html).toContain("border-dashed");
    expect(html).toContain("Bản đồ nhóm cơ");
    expect(html).not.toContain("<img");
  });

  it("renders safe /media images", () => {
    const html = renderMarkdown("![TDEE](/media/knowledge/cach-tinh-tdee-theo-muc-van-dong-thuc-te/tdee-pie.png)");
    expect(html).toContain("<img");
    expect(html).toContain('src="/media/knowledge/cach-tinh-tdee-theo-muc-van-dong-thuc-te/tdee-pie.png"');
    expect(html).toContain("TDEE");
  });

  it("rejects unsafe image urls", () => {
    const html = renderMarkdown("![x](javascript:alert(1))");
    expect(html).not.toContain("<img");
    expect(html).not.toContain("javascript:");
  });
});

describe("htmlToMarkdown", () => {
  it("converts bold, italic, and lists", () => {
    expect(htmlToMarkdown("<p>Hello <b>world</b></p>")).toBe("Hello **world**");
    expect(htmlToMarkdown("<p><i>hi</i></p>")).toBe("_hi_");
    expect(htmlToMarkdown("<ul><li>Ngực</li><li>Lưng</li></ul>")).toBe("- Ngực\n- Lưng");
    expect(htmlToMarkdown("<ol><li>A</li><li>B</li></ol>")).toBe("1. A\n2. B");
  });

  it("handles chrome list wrappers and nested bold", () => {
    expect(htmlToMarkdown("<ul><li><div><b>Ngực</b></div></li></ul>")).toBe("- **Ngực**");
    expect(htmlToMarkdown("<p><b><i>x</i></b></p>")).toBe("**_x_**");
  });

  it("round-trips a coach note", () => {
    const md = "## Mục tiêu\n- Tập **4 buổi**/tuần\n- Nghỉ đủ";
    const again = htmlToMarkdown(renderMarkdown(md));
    expect(again).toContain("## Mục tiêu");
    expect(again).toContain("- Tập **4 buổi**/tuần");
    expect(again).toContain("- Nghỉ đủ");
  });
});
