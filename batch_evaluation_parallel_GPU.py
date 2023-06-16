#!/scratch1/NCEPDEV/global/Tse-chun.Chen/anaconda3/envs/ltn/bin/python
# salloc --account=gsienkf --partition=bigmem --time=00:59:00 --nodes=1 --ntasks=40
import torch
from training import create_checkpoint_filename, compute_skill
from check_model import read_model
import numpy as np
import os, math
from test_train_valid_splits import test_train_valid_splits
from training import Dataset_np as Dataset
from torch.utils.data import DataLoader
#from torchmetrics.functional import mean_squared_error

torch.set_num_threads(int(os.cpu_count()/2))

def my_eval_model(model, test_Loader, device):
  y_pred = torch.zeros(test_Loader.dataset.out.shape)
  y = torch.zeros(test_Loader.dataset.out.shape)
  bs = test_Loader.batch_size
  with torch.set_grad_enabled(False):
    model.eval()
    for batch_id, (X_, y_) in enumerate(test_Loader):
        X_.to(device)
        y_pred_ = model(X_)
        y[batch_id*bs:batch_id*bs+y_.shape[0],:,:,:]=copy.deepcopy(y_)
        y_pred[batch_id*bs:batch_id*bs+y_.shape[0],:,:,:]=copy.deepcopy(y_pred_)
  return y_pred, y

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
ptmp=['tpsuvq', 'online', 't', 4, '1', '4096', 3, 0.25, 8, 'mse', 0.0001, 1., 'sub', 375, 3, 0.7]

#load model
print("loading model")
fntmp = create_checkpoint_filename(ptmp)
model, hyperparam = read_model(fntmp, True, device=device)
model = torch.nn.DataParallel(model)
model.to(device)

#load test data once for efficiency
print("loading data")
splits = test_train_valid_splits(hyperparam['testset'], 
                hyperparam["end_of_training_day"], hyperparam["training_validation_length_days"])
test_slice = splits["test_slice"]
test_set = Dataset(idx_include=test_slice, **hyperparam) # initiate dataset object
batch_size=math.ceil(test_set.out.shape[0]/8)
test_Loader = DataLoader(test_set, batch_size=batch_size,num_workers=1) # set up data loader

print("Computing forward model")
y_pred, y = my_eval_model(model, test_Loader, device)

# check that y was assembled correctley
#mean_squared_error(y, test_Loader.dataset.out)

# compute skill
print("Computing skill")
skill = compute_skill(y, y_pred)
fnout = os.path.join('npys','expvar_'+os.path.split(fntmp)[-1])
np.save(fnout, skill)


