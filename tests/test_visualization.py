"""
Lightweight tests for visualization/*.py — chart_generator, diagram_generator,
knowledge_graph_generator. All pure-Python/local rendering, no network or
GPU needed, so these run instantly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_chart_extracts_real_numbers_when_present():
    from visualization.chart_generator import extract_chart_spec

    context = "Accuracy: 92, Precision: 88, Recall: 81"
    spec = extract_chart_spec("plot the metrics", context)
    assert not spec.is_placeholder
    assert "Accuracy" in spec.categories
    assert 92.0 in spec.values


def test_chart_falls_back_to_placeholder_without_numbers():
    from visualization.chart_generator import extract_chart_spec

    spec = extract_chart_spec("plot something", "no numbers here at all")
    assert spec.is_placeholder
    assert len(spec.categories) > 0


def test_chart_renders_without_error():
    from visualization.chart_generator import extract_chart_spec, render_chart

    spec = extract_chart_spec("plot", "Accuracy: 90, Loss: 5")
    fig = render_chart(spec)
    assert fig is not None


def test_diagram_splits_sequential_steps():
    from visualization.diagram_generator import extract_diagram_spec

    context = "First, data is collected. Then, it is cleaned. Finally, the model is trained."
    spec = extract_diagram_spec("how does the pipeline work", context)
    assert not spec.is_placeholder
    assert len(spec.steps) >= 2


def test_diagram_produces_valid_mermaid_syntax():
    from visualization.diagram_generator import generate_mermaid

    mermaid = generate_mermaid("how does it work", "First, A happens. Then, B happens.")
    assert mermaid.startswith("flowchart TD")
    assert "-->" in mermaid


def test_concept_map_extracts_multiword_concepts():
    from visualization.knowledge_graph_generator import build_concept_map

    docs = [
        "Gradient Descent minimizes the Loss Function.",
        "Gradient Descent is used with Backpropagation in Neural Networks.",
    ]
    spec = build_concept_map(docs)
    assert not spec.is_placeholder
    assert "Gradient Descent" in spec.concepts
    assert len(spec.edges) > 0


def test_concept_map_placeholder_on_empty_corpus():
    from visualization.knowledge_graph_generator import build_concept_map

    spec = build_concept_map([])
    assert spec.is_placeholder


def test_concept_map_renders_without_error():
    from visualization.knowledge_graph_generator import generate_concept_map

    docs = ["Gradient Descent minimizes the Loss Function used by Neural Networks."]
    spec, fig = generate_concept_map(docs)
    assert fig is not None


def test_image_generator_reports_unavailable_by_default():
    from visualization.image_generator import generate_concept_image

    result = generate_concept_image("a metaphor for gradient descent")
    assert result.available is False
    assert result.message


if __name__ == "__main__":
    test_chart_extracts_real_numbers_when_present()
    test_chart_falls_back_to_placeholder_without_numbers()
    test_chart_renders_without_error()
    test_diagram_splits_sequential_steps()
    test_diagram_produces_valid_mermaid_syntax()
    test_concept_map_extracts_multiword_concepts()
    test_concept_map_placeholder_on_empty_corpus()
    test_concept_map_renders_without_error()
    test_image_generator_reports_unavailable_by_default()
    print("All visualization tests passed.")
