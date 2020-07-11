# Author: Kaylani Bochie
# github.com/kaylani2
# kaylani AT gta DOT ufrj DOT br

### K: Model: 2D CNN

import pandas as pd
import numpy as np
import sys
import time
import keras.utils
from keras.utils import to_categorical
from sklearn.model_selection import PredefinedSplit
from sklearn.model_selection import GridSearchCV
from sklearn.tree import DecisionTreeClassifier
import time
from keras.models import Sequential
from keras.layers import Dense, Dropout
from keras.optimizers import RMSprop
from keras.optimizers import Adam
from keras.wrappers.scikit_learn import KerasClassifier
from keras import metrics
from keras.constraints import maxnorm
from keras.models import Sequential
from keras.layers import Dense, Dropout
from keras.optimizers import RMSprop
from keras.optimizers import Adam
from keras import metrics
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.metrics import confusion_matrix, precision_score, recall_score
from sklearn.metrics import f1_score, classification_report, accuracy_score
from sklearn.metrics import cohen_kappa_score, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.model_selection import PredefinedSplit
from sklearn.model_selection import GridSearchCV


###############################################################################
## Define constants
###############################################################################
# Random state for reproducibility

STATES = [0, 10, 100, 1000, 10000]
STATE = 0
#for STATE in STATES:
np.random.seed (STATE)

pd.set_option ('display.max_rows', None)
pd.set_option ('display.max_columns', 5)

BOT_IOT_DIRECTORY = '../../../../datasets/bot-iot/'
BOT_IOT_FEATURE_NAMES = 'UNSW_2018_IoT_Botnet_Dataset_Feature_Names.csv'
BOT_IOT_FILE_5_PERCENT_SCHEMA = 'UNSW_2018_IoT_Botnet_Full5pc_{}.csv' # 1 - 4
FIVE_PERCENT_FILES = 4
BOT_IOT_FILE_FULL_SCHEMA = 'UNSW_2018_IoT_Botnet_Dataset_{}.csv' # 1 - 74
FULL_FILES = 74
FILE_NAME = BOT_IOT_DIRECTORY + BOT_IOT_FILE_5_PERCENT_SCHEMA#FULL_SCHEMA
FEATURES = BOT_IOT_DIRECTORY + BOT_IOT_FEATURE_NAMES
NAN_VALUES = ['?', '.']
TARGET = 'attack'

###############################################################################
## Load dataset
###############################################################################
df = pd.DataFrame ()
for fileNumber in range (1, FIVE_PERCENT_FILES + 1):#FULL_FILES + 1):
  print ('Reading', FILE_NAME.format (str (fileNumber)))
  aux = pd.read_csv (FILE_NAME.format (str (fileNumber)),
                     #names = featureColumns,
                     index_col = 'pkSeqID',
                     dtype = {'pkSeqID' : np.int32}, na_values = NAN_VALUES,
                     low_memory = False)
  df = pd.concat ([df, aux])


###############################################################################
## Display generic (dataset independent) information
###############################################################################
#print ('Dataframe shape (lines, columns):', df.shape, '\n')
#print ('First 5 entries:\n', df [:5], '\n')
#print ('entries:\n', df [4000000//4 - 5:4000000//4 + 5], '\n')
df.info (verbose = True)

print ('\nDataframe contains NaN values:', df.isnull ().values.any ())
nanColumns = [i for i in df.columns if df [i].isnull ().any ()]
print ('Number of NaN columns:', len (nanColumns))
print ('NaN columns:', nanColumns, '\n')


###############################################################################
## Display specific (dataset dependent) information
###############################################################################
print ('\nAttack types:', df ['attack'].unique ())
print ('Attack distribution:')
print (df ['attack'].value_counts ())
print ('\nCateogry types:', df ['category'].unique ())
print ('Cateogry distribution:')
print (df ['category'].value_counts ())
print ('\nSubcategory types:', df ['subcategory'].unique ())
print ('Subcategory distribution:')
print (df ['subcategory'].value_counts ())


###############################################################################
## Data pre-processing
###############################################################################
#df.replace ( ['NaN', 'NaT'], np.nan, inplace = True)
#df.replace ('?', np.nan, inplace = True)
#df.replace ('Infinity', np.nan, inplace = True)

###############################################################################
### Remove columns with only one value
print ('\nColumn | # of different values')
# nUniques = df.nunique () ### K: Takes too long. WHY?
nUniques = []
for column in df.columns:
  nUnique = df [column].nunique ()
  nUniques.append (nUnique)
  print (column, '|', nUnique)

print ('\nRemoving attributes that have only one (or zero) sampled value.')
for column, nUnique in zip (df.columns, nUniques):
  if (nUnique <= 1): # Only one value: DROP.
    df.drop (axis = 'columns', columns = column, inplace = True)

print ('\nColumn | # of different values')
for column in df.columns:
  nUnique = df [column].nunique ()
  print (column, '|', nUnique)

###############################################################################
### Remove redundant columns
### K: These columns are numerical representations of other existing columns.
redundantColumns = ['state_number', 'proto_number', 'flgs_number']
print ('\nRemoving redundant columns:', redundantColumns)
df.drop (axis = 'columns', columns = redundantColumns, inplace = True)

###############################################################################
### Remove NaN columns (with a lot of NaN values)
print ('\nColumn | NaN values')
print (df.isnull ().sum ())
print ('Removing attributes with more than half NaN values.')
df = df.dropna (axis = 'columns', thresh = df.shape [0] // 2)
print ('Dataframe contains NaN values:', df.isnull ().values.any ())
print ('\nColumn | NaN values (after dropping columns)')
print (df.isnull ().sum ())

###############################################################################
### Input missing values
### K: Look into each attribute to define the best inputing strategy.
### K: NOTE: This must be done after splitting to dataset to avoid data leakge.
df ['sport'].replace ('-1', np.nan, inplace = True)
df ['dport'].replace ('-1', np.nan, inplace = True)
### K: Negative port values are invalid.
columsWithMissingValues = ['sport', 'dport']
### K: Examine values.
for column in df.columns:
  nUnique = df [column].nunique ()
for column, nUnique in zip (df.columns, nUniques):
    if (nUnique < 5):
      print (column, df [column].unique ())
    else:
      print (column, 'unique values:', nUnique)

# sport  unique values: 91168     # most_frequent?
# dport  unique values: 115949    # most_frequent?
imputingStrategies = ['most_frequent', 'most_frequent']


###############################################################################
### Handle categorical values
### K: Look into each attribute to define the best encoding strategy.
df.info (verbose = False)
### K: dtypes: float64 (11), int64 (8), object (9)
myObjects = list (df.select_dtypes ( ['object']).columns)
print ('\nObjects:', myObjects, '\n')
### K: Objects:
  # 'flgs',
  # 'proto',
  # 'saddr',
  # 'sport',
  # 'daddr',
  # 'dport',
  # 'state',
# LABELS:
  # TARGET,
  # 'subcategory'

print ('\nCheck for high cardinality.')
print ('Column | # of different values | values')
for column in myObjects:
  print (column, '|', df [column].nunique (), '|', df [column].unique ())

### K: NOTE: saddr and daddr (source address and destination address) may incur
### into overfitting for a particular scenario of computer network. Since the
### classifier will use these IPs and MACs to aid in classifying the traffic.
### We may want to drop these attributes to guarantee IDS generalization.
df.drop (axis = 'columns', columns = 'saddr', inplace = True)
df.drop (axis = 'columns', columns = 'daddr', inplace = True)

print ('\nHandling categorical attributes (label encoding).')
from sklearn.preprocessing import LabelEncoder
myLabelEncoder = LabelEncoder ()
df ['flgs'] = myLabelEncoder.fit_transform (df ['flgs'])
df ['proto'] = myLabelEncoder.fit_transform (df ['proto'])
df ['sport'] = myLabelEncoder.fit_transform (df ['sport'].astype (str))
df ['dport'] = myLabelEncoder.fit_transform (df ['dport'].astype (str))
df ['state'] = myLabelEncoder.fit_transform (df ['state'])
print ('Objects:', list (df.select_dtypes ( ['object']).columns))

###############################################################################
### Drop unused targets
### K: NOTE: category and subcategory are labels for different
### applications, not attributes. They must not be used to aid classification.
print ('\nDropping category and subcategory.')
print ('These are labels for other scenarios.')
df.drop (axis = 'columns', columns = 'category', inplace = True)
df.drop (axis = 'columns', columns = 'subcategory', inplace = True)


###############################################################################
## Encode Label
###############################################################################
### K: Binary classification. Already encoded.

###############################################################################
## Split dataset into train, validation and test sets
###############################################################################
from sklearn.model_selection import train_test_split
TEST_SIZE = 2/10
VALIDATION_SIZE = 1/4
print ('\nSplitting dataset (test/train):', TEST_SIZE)
X_train_df, X_test_df, y_train_df, y_test_df = train_test_split (
                                               df.iloc [:, :-1],
                                               df.iloc [:, -1],
                                               test_size = TEST_SIZE,
                                               random_state = STATE,)
                                               #shuffle = False)
print ('\nSplitting dataset (validation/train):', VALIDATION_SIZE)
X_train_df, X_val_df, y_train_df, y_val_df = train_test_split (
                                             X_train_df,
                                             y_train_df,
                                             test_size = VALIDATION_SIZE,
                                             random_state = STATE,)
                                             #shuffle = False)
X_train_df.sort_index (inplace = True)
y_train_df.sort_index (inplace = True)
X_val_df.sort_index (inplace = True)
y_val_df.sort_index (inplace = True)
X_test_df.sort_index (inplace = True)
y_test_df.sort_index (inplace = True)
#X_train_df.sort_values  (by = 'pkSeqID', inplace = True)
print ('X_train_df shape:', X_train_df.shape)
print ('y_train_df shape:', y_train_df.shape)
print ('X_val_df shape:', X_val_df.shape)
print ('y_val_df shape:', y_val_df.shape)
print ('X_test_df shape:', X_test_df.shape)
print ('y_test_df shape:', y_test_df.shape)


###############################################################################
## Imput missing data
###############################################################################
### K: NOTE: Only use derived information from the train set to avoid leakage.

from sklearn.impute import SimpleImputer
for myColumn, myStrategy in zip (columsWithMissingValues, imputingStrategies):
  myImputer = SimpleImputer (missing_values = np.nan, strategy = myStrategy)
  myImputer.fit (X_train_df [myColumn].values.reshape (-1, 1))
  X_train_df [myColumn] = myImputer.transform (X_train_df [myColumn].values.reshape (-1, 1))
  X_val_df [myColumn] = myImputer.transform (X_val_df [myColumn].values.reshape (-1, 1))
  X_test_df [myColumn] = myImputer.transform (X_test_df [myColumn].values.reshape (-1, 1))


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
### K: NOTE: Only use derived information from the train set to avoid leakage.
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
print ('\nApplying normalization.')
startTime = time.time ()
scaler = StandardScaler ()
#scaler = MinMaxScaler (feature_range = (0, 1))
scaler.fit (X_train)
X_train = scaler.transform (X_train)
X_val = scaler.transform (X_val)
X_test = scaler.transform (X_test)
print (str (time.time () - startTime), 'to normalize data.')


###############################################################################
## Create learning model (2D CNN) and tune hyperparameters
###############################################################################

###############################################################################
## Data reshaping
SAMPLE_2D_SIZE = X_train.shape [1] # 7x7

X_train.resize ( (X_train.shape[0], SAMPLE_2D_SIZE, SAMPLE_2D_SIZE))
X_train = X_train.reshape ( (X_train.shape[0], 7, 7, 1))
X_val.resize ( (X_val.shape[0], SAMPLE_2D_SIZE, SAMPLE_2D_SIZE))
X_val = X_val.reshape ( (X_val.shape[0], 7, 7, 1))
X_test.resize ( (X_test.shape[0], SAMPLE_2D_SIZE, SAMPLE_2D_SIZE))

print (train_features.shape)


###############################################################################
## Hyperparameter tuning
test_fold = np.repeat ([-1, 0], [X_train.shape [0], X_val.shape [0]])
myPreSplit = PredefinedSplit (test_fold)

###############################################################################
## Finished model


model = models.Sequential ()
model.add (layers.Conv2D (64, (3, 3), activation = 'relu',
                          input_shape = (7, 7, 1),
                          kernel_initializer = initializer))
model.add (layers.MaxPooling2D ( (3, 3)))
model.add (layers.Conv2D (64, (2, 2), activation = 'relu'))
model.add (layers.MaxPooling2D ( (2, 2)))
model.add (layers.Flatten ())
model.add (layers.Dense (64, activation = 'relu',
                         kernel_initializer = initializer))
model.add (layers.Dense (1, activation = 'sigmoid',
                         kernel_initializer = initializer))

###############################################################################
## Compile the network
###############################################################################
LEARNING_RATE = 0.01
model.compile (optimizer = keras.optimizers.Adam (lr = LEARNING_RATE),
               loss = keras.losses.BinaryCrossentropy (),
               metrics = ['binary_accuracy', metrics.Precision ()])

model.summary ()





###############################################################################
## Fit the network
###############################################################################
NUMBER_OF_EPOCHS = 2
BATCH_SIZE = 32
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
print (str (time.time () - startTime), 's to train model.')


###############################################################################
## Analyze results
###############################################################################
X_pred_val = bestModel.predict (X_val)
print (X_pred_val)
print (X_val)
print ('Train error:', mean_squared_error (bestModel.predict (X_train),
                                           X_train))

print ('Validation error:', mean_squared_error (X_pred_val, X_val))

SAMPLES = 50
print ('Error on first', SAMPLES, 'samples:')
for pred_sample, real_sample in zip (X_pred_val [:SAMPLES], X_val [:SAMPLES]):
  print ('MSE (pred, real)')
  print (mean_squared_error (pred_sample, real_sample))


### K: NOTE: Only look at test results when publishing...
#sys.exit ()
#X_pred_test = bestModel.predict (X_test)
#print ('Test error:', mean_squared_error (X_pred_test, X_test))
#for pred_sample, real_sample, label in zip (X_pred_test, X_test, y_test):
#  print ('MSE (pred, real) | Label')
#  print (mean_squared_error (pred_sample, real_sample), '|', label)
#### @TODO: Plot ROC on test set
