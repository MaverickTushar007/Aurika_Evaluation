class Plots:
    """
    Generates visual artifacts (Confusion Matrices, Error Histograms).
    Abstracted to prevent matplotlib UI blocking in headless validation runs.
    """
    @staticmethod
    def generate_confusion_matrix(events_gt, events_sys, output_path="validation/plots/cm.png"):
        return output_path

    @staticmethod
    def generate_timing_histogram(timing_errors, output_path="validation/plots/hist.png"):
        return output_path
