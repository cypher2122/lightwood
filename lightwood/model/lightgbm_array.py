import numpy as np
import pandas as pd
from typing import Dict, List, Set, Union

from lightwood.api import dtype
from lightwood.helpers.log import log
from lightwood.model.base import BaseModel
from lightwood.model.lightgbm import LightGBM
from lightwood.data.encoded_ds import EncodedDs, ConcatedEncodedDs


class LightGBMArray(BaseModel):
    models: List[LightGBM]
    n_ts_predictions:  int
    submodel_stop_after: float
    target: str

    def __init__(self, stop_after: int, target: str, dtype_dict: Dict[str, str], input_cols: List[str], n_ts_predictions: int):
        super().__init__(stop_after)
        self.submodel_stop_after = stop_after/n_ts_predictions
        self.target = target
        dtype_dict[target] = dtype.float
        self.models = [LightGBM(self.submodel_stop_after, target, dtype_dict, input_cols, use_optuna=False)
                       for _ in range(n_ts_predictions)]
        self.n_ts_predictions = n_ts_predictions  # for time series tasks, how long is the forecast horizon

    def fit(self, ds_arr: List[EncodedDs]) -> None:
        log.info('Started fitting LGBM models for array prediction')

        for timestep in range(self.n_ts_predictions):
            if timestep > 0:
                for fold in range(len(ds_arr)):
                    ds_arr[fold].data_frame[self.target] = ds_arr[fold].data_frame[f'{self.target}_timestep_{timestep}']
            self.models[timestep].fit(ds_arr) # @TODO: this call should be parallelized

    def __call__(self, ds: Union[EncodedDs, ConcatedEncodedDs]) -> pd.DataFrame:
        length = sum(ds.encoded_ds_lenghts) if isinstance(ds, ConcatedEncodedDs) else len(ds)
        ydf = pd.DataFrame(0,  # zero-filled
                           index=np.arange(length),
                           columns=[f'prediction_{i}' for i in range(self.n_ts_predictions)])

        for timestep in range(self.n_ts_predictions):
            ydf[f'prediction_{timestep}'] = self.models[timestep](ds)

        ydf['prediction'] = ydf.values.tolist()
        return ydf[['prediction']]