_model_cache = {}

def get_model():
    from funasr import AutoModel
    return AutoModel

def request_model(model_id, init_func):
    if model_id not in _model_cache:
        automodel_class = get_model()
        _model_cache[model_id] = init_func(automodel_class)
    return _model_cache[model_id]
