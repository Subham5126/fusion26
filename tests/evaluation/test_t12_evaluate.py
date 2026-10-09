import pytest
import numpy as np

from scripts.evaluate import generate_synthetic_scene, run_evaluation
from orbittrace.evaluation.evaluator import create_sequence_splits

def test_t12_deterministic_generation():
    seq1, pixels1, truth1 = generate_synthetic_scene("seq1", seed=42)
    seq2, pixels2, truth2 = generate_synthetic_scene("seq1", seed=42)
    
    assert seq1.model_dump() == seq2.model_dump()
    assert len(pixels1) == len(pixels2)
    for p1, p2 in zip(pixels1, pixels2):
        np.testing.assert_array_equal(p1, p2)
        
    assert [(gt.x, gt.y) for gt in truth1] == [(gt.x, gt.y) for gt in truth2]

def test_t12_splits_no_overlap():
    sequence_ids = [f"seq-{i}" for i in range(50)]
    splits = create_sequence_splits(sequence_ids, dev_ratio=0.4, val_ratio=0.2, test_ratio=0.4, seed=26)
    
    dev = set(splits["development"])
    val = set(splits["validation"])
    test = set(splits["test"])
    
    assert not dev.intersection(val)
    assert not dev.intersection(test)
    assert not val.intersection(test)
    assert len(dev) + len(val) + len(test) == 50

def test_t12_empty_and_negative_sequences():
    # Because of our 20% empty chance, we can search for a seed that produces an empty scene
    found_empty = False
    for seed in range(100):
        _, _, truth = generate_synthetic_scene("seq_test", seed=seed)
        if len(truth) == 0:
            found_empty = True
            break
            
    assert found_empty, "Generator must support producing empty/negative sequences."

def test_t12_no_ground_truth_leakage():
    # The analyze pipeline is only passed seq_input and pixels.
    # We verify that truth is separate and not attached to sequence input
    seq, pixels, truth = generate_synthetic_scene("seq1", seed=10)
    assert not hasattr(seq, "ground_truth")
    assert not hasattr(seq.frames[0], "ground_truth")
    # And run_evaluation prints the report but does not crash
