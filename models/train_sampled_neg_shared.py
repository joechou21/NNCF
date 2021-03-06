# sampled neg_sharing
import numpy as np
import time
from utilities import get_cur_time, nan_detection
from data_utils import group_shuffle_train
from train_base import TrainerBase

class Trainer(TrainerBase):
    def __init__(self, model_dict, conf, data_helper):
        super(Trainer, self).__init__(model_dict, conf, data_helper)
        self.model_train = model_dict['model_sampled_neg_shared']
        self.neg_sign = np.array([-1], dtype='int32') \
            if conf.loss == 'skip-gram' else 0
        self.sample_batch = data_helper.sampler_dict['sample_batch']
        _num_in_train = np.max(data_helper.data['train'], axis=0) + 1
        self._iidx = {'user': np.arange(_num_in_train[0]),
                      'item': np.arange(_num_in_train[1])}

    def train(self, eval_scheme=None, use_async_eval=True):
        model_train = self.model_train
        conf = self.conf
        data_helper = self.data_helper
        train = data_helper.data['train']
        C = data_helper.data['C']
        num_negatives = conf.num_negatives
        sample_batch = self.sample_batch
        train_batch_n = np.zeros((num_negatives, 3))
        response_batch = np.ones((conf.batch_size_p + num_negatives, #dummy
                                  1 + num_negatives))
        response_batch[:, 1:] = self.neg_sign

        train_time = []
        for epoch in range(conf.max_epoch + 1):
            bb, b = 0, conf.batch_size_p
            train = group_shuffle_train(train, by='item', \
                chop=conf.chop_size, iidx=self._iidx['item'])
            cost, it = 0, 0

            t_start = time.time()
            while epoch > 0 and bb < len(train):
                it += 1
                b = bb + conf.batch_size_p
                if b > len(train):
                    # get rid of uneven tail so no need to dynamically adjust batch_size_p
                    break
                train_batch_p = train[bb: b]
                train_batch_n[:, 1] = sample_batch(train_batch_n.shape[0])
                train_batch = np.vstack((train_batch_p, train_batch_n))
                user_batch = train_batch[:, 0]
                item_batch = train_batch[:, 1]
                cost += model_train.train_on_batch([user_batch, item_batch],
                    [response_batch])
                bb = b
            if epoch > 0:
                train_time.append(time.time() - t_start)
            print get_cur_time(), 'epoch %d (%d it)' % (epoch, it), \
                'cost %.5f' % (cost / it if it > 0 else -1),
            nan_detection('cost', cost)
            if eval_scheme is None:
                print ''
            else:
                async_eval = True \
                    if use_async_eval and epoch != conf.max_epoch else False
                try: ps[-1].join()
                except: pass
                ps = self.test(eval_scheme, use_async_eval=async_eval)
        print 'Training time (sec) per epoch:', np.mean(train_time)
