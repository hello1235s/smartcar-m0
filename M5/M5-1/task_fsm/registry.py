from .nodes import WaitForTrigger, NavigateTo, DetectTarget, ExecuteGrasp, SpeakTTS

REGISTRY = {cls.__name__: cls for cls in [WaitForTrigger, NavigateTo, DetectTarget, ExecuteGrasp, SpeakTTS]}
