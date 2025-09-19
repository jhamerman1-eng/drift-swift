from libs.risk.crash_detector import CrashDetectorV2
def test_crash_detector_stub():
    det = CrashDetectorV2()
    sig = det.update([1]*9 + [2])  # minimal series
    assert hasattr(sig, 'triggered')
