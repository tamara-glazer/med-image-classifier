'''
Prediction Challenge Loop
'''
import pandas as pd
import sklearn
import datetime
import timeit

from sklearn.model_selection import cross_val_score
from sklearn.model_selection import ParameterGrid

from sklearn.tree import DecisionTreeRegressor
from sklearn.linear_model import Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor

import pipeline as pipe


def find_best_model(models, parameters_grid, x_train, outcome_label):
    '''
    Cross-validation to find the best model, given parameters
    '''
    results_df =  pd.DataFrame(columns=('model_name',
                                        'parameters',
                                        'MSE',
                                        'time_to_run'))
    min_mse = float('inf')
    best_model = ""
    best_model = ""
    best_parameter = ""
    start_time = timeit.default_timer()

    for model_key in models:
        print("Starting " + model_key + " at " + str(datetime.datetime.now()))
        model = models[model_key]
        parameter_values = parameters_grid[model_key]
        for parameter in ParameterGrid(parameter_values):
            s = timeit.default_timer()
            model.set_params(**parameter)

            # Calculate MSE using 5-fold cross validation
            # Change signs because scoring is negative MSE
            scores = -cross_val_score(estimator=model,
                                      X=x_train.drop(outcome_label, axis=1),
                                      y=x_train[outcome_label], # series or dataframe preferred?
                                      cv=5,
                                      scoring='neg_mean_squared_error')
            print('doing okay')
        
            mse = scores.mean()
            time = timeit.default_timer() - start_time
            results_df.loc[(len(results_df))] = [model_key, parameter,
                                                 mse, time]

            # Update "winner"
            if (mse < min_mse):
                min_mse = mse
                best_model = model
                best_parameter = parameter
                best_model_type = model_key

    elapsed = timeit.default_timer() - start_time


    print(results_df)
    print("Lowest MSE " + str(min_mse))
    print("Best Model " + str(best_model))
    print("Best Parameter " + str(best_parameter))
    print('Total Time: ', elapsed)
    

    # Fit best model and best parameter on full training dataset
    best_model.set_params(**best_parameter)
    best_model.fit(x_train.drop(outcome_label, axis=1),
                   x_train[outcome_label])

    return best_model


# THIS IS NOT READY
def main():
    '''
    EXECUTE FULL LOOP.
    '''

    models = {'Tree': DecisionTreeRegressor(max_depth=10),
              'Lasso': Lasso(alpha=0.1),
              'Ridge': Ridge(alpha=.5),
              'Forest': RandomForestRegressor(max_depth=2)
              }

    parameters_grid = {'Tree': {'max_depth': [10]},#, 20, 30]},
                       'Lasso': {'alpha': [0.01]},#, 0.075, 0.1]},
                       'Ridge': {'alpha': [0.01]},#, 0.075, 0.1]},
                       'Forest': {'max_depth': [10]}
                       }

    outcome = 'pathology'
    train, test, test_ids = pipe.go() ### UPDATE THIS ###

    best_model = find_best_model(models, parameters_grid, train, outcome)

    #Run predictions on test data and save file
    y_hats = best_model.predict(test)

    results  = pd.DataFrame(list(zip(test_ids, y_hats)),
                            columns =['id', 'y_hat'])

    results.to_csv('results.csv', index=False)

if __name__ == '__main__':
    main()