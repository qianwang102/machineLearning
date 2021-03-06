# Authors: Kaylani Bochie and Ernesto Rodríguez
# github.com/kaylani2
# github.com/ernestorodg

###############################################################################
## Analyse Bezerra's dataset for intrusion detection using autoencoders
###############################################################################

# We import everything used on all the codes, so it is easier to scale or reproduce.

import sys
import time
import pandas as pd
import os
import numpy as np
from numpy import mean, std
from unit import remove_columns_with_one_value, remove_nan_columns, load_dataset
from unit import display_general_information, display_feature_distribution
from collections import Counter
from sklearn.impute import SimpleImputer
from sklearn.svm import SVC, LinearSVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, OrdinalEncoder
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from sklearn.metrics import confusion_matrix, precision_score, recall_score
from sklearn.metrics import f1_score, classification_report, accuracy_score
from sklearn.metrics import cohen_kappa_score, mean_squared_error
from sklearn.model_selection import train_test_split, PredefinedSplit
from sklearn.model_selection import GridSearchCV, RepeatedStratifiedKFold
from sklearn.model_selection import cross_val_score
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest
from sklearn.feature_selection import f_classif, chi2, mutual_info_classif
from sklearn.utils import class_weight
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
import keras.utils
from keras import metrics
from keras.utils import to_categorical
from keras.models import Sequential
from keras.layers import Dense, Dropout
from keras.layers import Conv2D, MaxPooling2D, Flatten, LSTM
from keras.optimizers import RMSprop, Adam
from keras.constraints import maxnorm
from numpy import empty
from keras.wrappers.scikit_learn import KerasClassifier
from keras.wrappers.scikit_learn import KerasRegressor




###############################################################################
## Define constants
###############################################################################

# Random state for reproducibility
try:
  # If defined at argv:
  STATE = int (sys.argv[1])
except:
  # If not defined, it will be 0
  STATE = 0
print ('STATE:', STATE)

####################################################################
# Load the dataset
####################################################################


df = load_dataset ()
print ("Data Loaded")
remove_columns_with_one_value (df, verbose = False)
remove_nan_columns (df, 0.6, verbose = False)
#making the final DataFrame
#dropping the number of the rows column
df = df.drop (df.columns [0], axis = 1)

#dropping unrelated columns
df.drop (axis = 'columns', columns= ['ts', 'te', 'sa', 'da'], inplace = True)


####################################################################
# Treating categorical data before splitting the dataset into the differents sets
####################################################################

cat_cols = df.columns[df.dtypes == 'O'] # Returns array with the columns that has Object types elements

# Check wether cat_cols is empty or not. If it is empty, do not do anything
if list (cat_cols):
    categories = [
        df[column].unique () for column in df[cat_cols]]

    for cat in categories:
        cat[cat == None] = 'missing'  # noqa

    # Replacing missing values
    categorical_imputer = SimpleImputer (missing_values = None,
                                        strategy = 'constant',
                                        fill_value = 'missing')

    df[cat_cols] = categorical_imputer.fit_transform (df[cat_cols])

    # Encoding the categorical data
    categorical_encoder = OrdinalEncoder (categories = categories)
    categorical_encoder.fit (df[cat_cols])
    df[cat_cols] = categorical_encoder.transform (df[cat_cols])

###############################################################################
## Split dataset into train, validation and test sets
###############################################################################
### Isolate attack and normal samples
mask = df[TARGET] == 0
# 0 == normal
df_normal = df[mask]
# 1 == attack
df_attack = df[~mask]

print ('Attack set:')
print (df_attack [TARGET].value_counts ())
print ('Normal set:')
print (df_normal [TARGET].value_counts ())



### Sample and drop random attacks
df_random_attacks = df_attack.sample (n = df_normal.shape [0], random_state = STATE)
df_attack = df_attack.drop (df_random_attacks.index)

### Assemble test set
df_test = pd.DataFrame ()
df_test = pd.concat ( [df_test, df_normal])
df_test = pd.concat ( [df_test, df_random_attacks])
print ('Test set:')
print (df_test [TARGET].value_counts ())



X_test_df = df_test.iloc [:, 1:]
y_test_df = df_test.iloc [:, 0]

### K: y_test is required to plot the roc curve in the end

###############################################################################
## Splitting the data
###############################################################################
df_train = df_attack
VALIDATION_SIZE = 1/4
print ('\nSplitting dataset (validation/train):', VALIDATION_SIZE)
X_train_df, X_val_df, y_train_df, y_val_df = train_test_split (
                                           df_train.iloc [:, :-1],
                                           df_train.iloc [:, -1],
                                           test_size = VALIDATION_SIZE,
                                           random_state = STATE,)


print ('X_train_df shape:', X_train_df.shape)
print ('y_train_df shape:', y_train_df.shape)
print ('X_val_df shape:', X_val_df.shape)
print ('y_val_df shape:', y_val_df.shape)
print ('X_test_df shape:', X_test_df.shape)
print ('y_test_df shape:', y_test_df.shape)


###############################################################################
## Convert dataframe to a numpy array
###############################################################################
print ('\nConverting dataframe to numpy array.')
X_train = X_train_df.values
y_train = y_train_df.values
X_val = X_val_df.values
y_val = y_val_df.values
X_test = X_test_df.values
y_test = y_test_df.values
print ('X_train shape:', X_train.shape)
print ('y_train shape:', y_train.shape)
print ('X_val shape:', X_val.shape)
print ('y_val shape:', y_val.shape)
print ('X_test shape:', X_test.shape)
print ('y_test shape:', y_test.shape)


###############################################################################
## Apply normalization
###############################################################################


print ('\nApplying normalization.')
startTime = time.time ()
scaler = StandardScaler ()
scaler.fit (X_train)
X_train = scaler.transform (X_train)
X_val = scaler.transform (X_val)
X_test = scaler.transform (X_test)
print (str (time.time () - startTime), 'to normalize data.')


'''
On this case there was not feature selection, but code can be
recycled


###############################################################################
## Feature selection
###############################################################################
NUMBER_OF_FEATURES = 4
print ('Selecting top', NUMBER_OF_FEATURES, 'features.')
startTime = time.time ()
#fs = SelectKBest (score_func = mutual_info_classif, k = NUMBER_OF_FEATURES)
### K: ~30 minutes to FAIL fit mutual_info_classif to 5% bot-iot
#fs = SelectKBest (score_func = chi2, k = NUMBER_OF_FEATURES) # X must be >= 0
### K: ~4 seconds to fit chi2 to 5% bot-iot (MinMaxScaler (0, 1))
fs = SelectKBest (score_func = f_classif, k = NUMBER_OF_FEATURES)
### K: ~4 seconds to fit f_classif to 5% bot-iot
fs.fit (X_train, y_train)
X_train = fs.transform (X_train)
X_val = fs.transform (X_val)
X_test = fs.transform (X_test)
print (str (time.time () - startTime), 'to select features.')
print ('X_train shape:', X_train.shape)
print ('y_train shape:', y_train.shape)
print ('X_val shape:', X_val.shape)
print ('y_val shape:', y_val.shape)
print ('X_test shape:', X_test.shape)
print ('y_test shape:', y_test.shape)
bestFeatures = []
for feature in range (len (fs.scores_)):
  bestFeatures.append ({'f': feature, 's': fs.scores_ [feature]})
  bestFeatures = sorted (bestFeatures, key = lambda k: k ['s'])
for feature in bestFeatures:
  print ('Feature %d: %f' % (feature ['f'], feature ['s']))
'''

##############################################################################
# Create learning model (Autoencoder) and tune hyperparameters
##############################################################################

'''
test_fold = np.repeat ( [-1, 0], [X_train.shape [0], X_val.shape [0]])
myPreSplit = PredefinedSplit (test_fold)
def create_model (learn_rate = 0.01, dropout_rate = 0.0, weight_constraint = 0):
    model = Sequential ()
    model.add (Dense (X_train.shape [1], activation = 'relu',
                   input_shape = (X_train.shape [1], )))
    model.add (Dense (32, activation = 'relu'))
    model.add (Dense (8,  activation = 'relu'))
    model.add (Dense (32, activation = 'relu'))
    model.add (Dense (X_train.shape [1], activation = None))
    model.compile (loss = 'mean_squared_error',
                optimizer = 'adam',
                metrics = ['mse'])
    return model

model = KerasRegressor (build_fn = create_model, verbose = 2)
batch_size = [30]#, 50]
epochs = [5, 10]
learn_rate = [0.01, 0.1]#, 0.2, 0.3]
dropout_rate = [0.0, 0.2]#, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
weight_constraint = [0]#1, 2, 3, 4, 5]
param_grid = dict (batch_size = batch_size, epochs = epochs,
                  dropout_rate = dropout_rate, learn_rate = learn_rate,
                  weight_constraint = weight_constraint)
grid = GridSearchCV (estimator = model, param_grid = param_grid,
                    scoring = 'neg_mean_squared_error', cv = myPreSplit,
                    verbose = 2, n_jobs = 16)

grid_result = grid.fit (np.vstack ((X_train, X_val)),#, axis = 1),
                       np.vstack ((X_train, X_val)))#, axis = 1))
print (grid_result.best_params_)

means = grid_result.cv_results_ ['mean_test_score']
stds = grid_result.cv_results_ ['std_test_score']
params = grid_result.cv_results_ ['params']
for mean, stdev, param in zip (means, stds, params):
    print ("%f (%f) with: %r" % (mean, stdev, param))

print ("Best: %f using %s" % (grid_result.best_score_, grid_result.best_params_))

sys.exit ()

'''

###############################################################################
## Final model
###############################################################################


NUMBER_OF_EPOCHS = 40
BATCH_SIZE = 50000
LEARNING_RATE = 0.001

INPUT_SHAPE = (X_train.shape [1], )

print ('\nCreating learning model.')
bestModel = Sequential ()
bestModel.add (Dense (X_train.shape [1], activation = 'relu',
                    input_shape = (X_train.shape [1], )))
bestModel.add (Dense (70, activation = 'relu'))
bestModel.add (Dense (2,  activation = 'relu'))
bestModel.add (Dense (70, activation = 'relu'))
bestModel.add (Dense (X_train.shape [1], activation = None))


###############################################################################
## Compile the network
###############################################################################
print ('\nCompiling the network.')
bestModel.compile (loss = 'mean_squared_error',
#bestModel.compile (loss = 'mean_absolute_error',
                 optimizer = Adam (lr = LEARNING_RATE),
                 metrics = ['mae', 'mse'])#,metrics.Precision ()])

print ('Model summary:')
bestModel.summary ()




###############################################################################
## Fit the network
###############################################################################
print ('\nFitting the network.')
startTime = time.time ()
history = bestModel.fit (X_train, X_train,
                       batch_size = BATCH_SIZE,
                       epochs = NUMBER_OF_EPOCHS,
                       verbose = 2, #1 = progress bar, not useful for logging
                       workers = 0,
                       use_multiprocessing = True,
                       #class_weight = 'auto',
                       validation_data = (X_val, X_val))
training_time = time.time () - startTime
print (str (training_time), 's to train model.')


###############################################################################
## Analyze results
###############################################################################
X_val_pred   = bestModel.predict (X_val)
X_train_pred = bestModel.predict (X_train)
print ('Train error:'     , mean_squared_error (X_train_pred, X_train))
print ('Validation error:', mean_squared_error (X_val_pred, X_val))

SAMPLES = 50
print ('Error on first', SAMPLES, 'samples:')
print ('MSE (pred, real)')
for pred_sample, real_sample in zip (X_val_pred [:SAMPLES], X_val [:SAMPLES]):
  print (mean_squared_error (pred_sample, real_sample))

THRESHOLD_SAMPLE_PERCENTAGE = 1/100

train_mse_element_wise = np.mean (np.square (X_train_pred - X_train), axis = 1)
val_mse_element_wise = np.mean (np.square (X_val_pred - X_val), axis = 1)

max_threshold_val = np.max (val_mse_element_wise)
print ('max_Thresh val:', max_threshold_val)



print ('samples:')
print (int (round (val_mse_element_wise.shape [0] *
         THRESHOLD_SAMPLE_PERCENTAGE)))

top_n_values_val = np.partition (-val_mse_element_wise,
                               int (round (val_mse_element_wise.shape [0] *
                                           THRESHOLD_SAMPLE_PERCENTAGE)))

top_n_values_val = -top_n_values_val [: int (round (val_mse_element_wise.shape [0] *
                                                  THRESHOLD_SAMPLE_PERCENTAGE))]


threshold = np.median (top_n_values_val)
print ('Thresh val:', threshold)



X_test_pred = bestModel.predict (X_test)
print (X_test_pred.shape)
print ('Test error:', mean_squared_error (X_test_pred, X_test))

y_pred = np.mean (np.square (X_test_pred - X_test), axis = 1)
y_test, y_pred = zip (*sorted (zip (y_test, y_pred)))
print ('\nLabel | MSE (pred, real) (ordered)')
for label, pred in zip (y_test, y_pred):
  print (label, '|', pred)

# 0 == normal
# 1 == attack
print ('\nMSE (pred, real) | Label (ordered)')
tp, tn, fp, fn = 0, 0, 0, 0
for label, pred in zip (y_test, y_pred):

  if ((pred >= threshold) and (label == 0)):
      tn += 1
  elif ((pred >= threshold) and (label == 1)):
      fn += 1
  elif ((pred < threshold) and (label == 1)):
      tp += 1
  elif ((pred < threshold) and (label == 0)):
      fp += 1

print ('Confusion matrix:')
print ('tp | fp')
print ('fn | tn\n\n')
print (tp, '|', fp)
print (fn, '|', tn)

print ('TP:', tp)
print ('TN:', tn)
print ('FP:', fp)
print ('FN:', fn)
