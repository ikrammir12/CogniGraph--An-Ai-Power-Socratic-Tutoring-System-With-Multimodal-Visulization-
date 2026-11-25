import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from router.multimodal_router import OutputMode, classify


def test_diagram_routing():
    assert classify("Can you explain the architecture of a CNN?") == OutputMode.DIAGRAM
    assert classify("What's the workflow for training a model?") == OutputMode.DIAGRAM


def test_concept_map_routing():
    assert classify("Show me a concept map of this course") == OutputMode.CONCEPT_MAP
    assert classify("What's the relationship between overfitting and regularization?") == OutputMode.CONCEPT_MAP
    assert classify("How are these topics related?") == OutputMode.CONCEPT_MAP


def test_graph_routing():
    assert classify("Plot the accuracy trend over epochs") == OutputMode.GRAPH
    assert classify("Show me a bar chart of the results") == OutputMode.GRAPH


def test_image_routing():
    assert classify("Draw a concept art metaphor for gradient descent") == OutputMode.IMAGE


def test_text_routing_default():
    assert classify("What is the definition of overfitting?") == OutputMode.TEXT


if __name__ == "__main__":
    test_diagram_routing()
    test_concept_map_routing()
    test_graph_routing()
    test_image_routing()
    test_text_routing_default()
    print("All router tests passed.")
