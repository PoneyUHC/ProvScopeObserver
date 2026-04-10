
import sys
from pathlib import Path


def build_processes_condition(process_names: list[str]) -> str:
    return "".join(f'comm == "{name}" || ' for name in process_names) + "false"


def build_script_config() -> str:
    return (
        "config = {\n"
        "\tmax_map_keys = 65535;\n"
        "\tprint_maps_on_exit = 0;\n"
        "\tmax_strlen = 150\n"
        "}\n\n"
    )


def main(process_names: list[str]) -> None:
    backend_dir = Path(__file__).resolve().parent
    template_dir = backend_dir / "templates"
    scripts_dir = backend_dir.parent / "run" / backend_dir.name / "scripts"

    scripts_dir.mkdir(parents=True, exist_ok=True)

    for template_path in sorted(template_dir.glob("*_template.bt")):
        output_path = scripts_dir / template_path.name.replace("_template", "")
        template = template_path.read_text()
        template = template.replace(
            "[TEMPLATE_PROCESS_NAMES]",
            build_processes_condition(process_names),
        )
        template = template.replace("[TEMPLATE_CONFIG]", build_script_config())
        output_path.write_text(template)


if __name__ == "__main__":
    process_names = sys.argv[1].split(",") if len(sys.argv) > 1 and sys.argv[1] else []
    main(process_names)
