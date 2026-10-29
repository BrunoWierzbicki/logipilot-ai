"""Gera relatório agendável com dados de demonstração em JSON."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.automation import classify_priority, summarize


def render_report(incidents: list[dict], date: str | None = None) -> str:
    summary = summarize(incidents)
    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Relatório automático — LogiPilot AI", "",
        f"**Gerado em:** {date}", "",
        "> Dados fictícios para demonstração; não representam operações reais.", "",
        "## Indicadores", "",
        f"- Total de ocorrências: **{summary['total']}**",
        f"- Ocorrências que exigem atenção: **{summary['exigem_atencao']}**", "",
        "| Prioridade | Quantidade |", "|---|---:|",
    ]
    for level, count in summary["por_prioridade"].items():
        lines.append(f"| {level} | {count} |")
    lines += ["", "## Ocorrências prioritárias", ""]
    urgent = [(classify_priority(i["description"]), i["description"]) for i in incidents]
    urgent = [item for item in urgent if item[0] in {"CRITICA", "ALTA"}]
    if urgent:
        lines += [f"- **{priority}** — {description}" for priority, description in urgent]
    else:
        lines += ["Nenhuma ocorrência crítica ou alta no conjunto analisado."]
    lines += ["", "## Automação executada", "", "Classificação por regras transparentes e relatório Markdown automático. Esta etapa não usa LLM.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/sample_incidents.json")
    parser.add_argument("--output", default="reports/relatorio_diario.md")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(data), encoding="utf-8")
    print(f"Relatório gerado: {output}")


if __name__ == "__main__":
    main()
