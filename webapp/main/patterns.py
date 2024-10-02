from .models import HiddenInput


def sidebar_create(
    classname: str,
    form_endpoint: str,
    inputs: list[str],
    hiddens: list[HiddenInput] = [],
) -> str:
    starts_with_vowel = len(classname) > 0 and classname[0].lower() in ("a", "e", "i", "o", "u")
    header = f"<h1>Create a{'n' if starts_with_vowel else ''} {classname}</h1>"
    hiddens_html = "".join(
        [
            f"""
            <input
                type="hidden"
                name="{h.name}"
                value="{h.value}"
            />
            """
            for h in hiddens
        ]
    )

    return f"""
        <section class="sidebar right" _="on closeModal add .closing then wait for animationend then remove me">
            {header}
            <form hx-post="{form_endpoint}" hx-swap="none">
                {"".join(inputs)}
                <div>
                    {hiddens_html}
                    <button>Create. Use SVG loader and checkmark for creation feedback.</button>
                    <button type="button" _="on click trigger closeModal">Abort</button>
                </div>
            </form>
        </section>
    """
