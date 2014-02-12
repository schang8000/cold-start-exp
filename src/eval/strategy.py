__author__ = 'shuochang'

import abc
import pandas as pd
import numpy as np


class BaseColdStartStrategy(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def gen_movie_list(self):
        """generate a sequence of movies to rate"""
        pass

    @abc.abstractmethod
    def write_train_test(self, train_name, test_name, n):
        """prepare the train and test files after applying the cold start strategy"""
        pass

    def get_output_name(self, name, appendix=None):
        new_name = name.split(".")
        new_name.insert(len(new_name)-1, self.name + '_' + appendix if appendix else self.name)
        return ".".join(new_name)


class GlobalColdStartStrategy(BaseColdStartStrategy):
    @abc.abstractmethod
    def gen_movie_list(self, train_df, n):
        """generate a sequence of movies to rate"""
        pass

    def write_train_test(self, train_fn, test_fn, select_fn, movie_fn,
                         train_this_fold, train_other_folds, test, n):
        # generate movie list and select only these to include in the training part
        # for this fold and combine with the other folds to make final training file
        movie_list = self.gen_movie_list(train_other_folds, n)
        train_this_fold['rated'] = train_this_fold.item.isin(movie_list)
        train_selected = train_this_fold[train_this_fold.rated].drop('rated', 1)
        train_final = pd.concat([train_other_folds, train_selected])
        # output to files
        pd.DataFrame({'movie': movie_list}).to_csv(self.get_output_name(train_fn, str(n)+'_'+movie_fn))
        train_this_fold.to_csv(self.get_output_name(train_fn, str(n)+'_'+select_fn), index=False)
        train_final.to_csv(self.get_output_name(train_fn, str(n)), header=False, index=False)
        test.to_csv(self.get_output_name(test_fn, str(n)), header=False, index=False)


class PopularityStrategy(GlobalColdStartStrategy):
    def __init__(self, name='popular'):
        self.name = name

    def gen_movie_list(self, train_df, n):
        num_rating = train_df.groupby('item')['rating'].count()
        num_rating.sort(ascending=False)
        return num_rating.index[:n]


class EntropyStrategy(GlobalColdStartStrategy):
    def __init__(self, name='entropy'):
        self.name = name

    def gen_movie_list(self, train_df, n):
        grp = train_df.groupby(['item', 'rating'])['user'].count()
        movies = grp.groupby(level=0).apply(self.entropy)
        movies.sort(ascending=False)
        return movies.index[:n]

    @staticmethod
    def entropy(x):
        ent = 0
        for p in x*1.0/x.sum():
            ent += -p*np.log(p)
        return ent