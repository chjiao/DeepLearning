import tensorflow as tf
from model import QFunction

import numpy as np
import random

def copy_params(src, dst):
    src_params = [v for v in tf.trainable_variables() if v.name.startswith(src.scope)]
    dst_params = [v for v in tf.trainable_variables() if v.name.startswith(dst.scope)]

    op = [d.assign(s) for s, d in zip(src_params, dst_params)]

    return op

def Hurber_loss(x, y, delta=1.0):
    error = tf.abs(y - x)
    cond = tf.less(error, delta)
    return tf.where(cond,
                    0.5*tf.square(error),
                    delta*error - 0.5*tf.square(delta))
class DQN:
    def __init__(self, input_shape, action_n, gamma=0.99, N=50000):
        self.N = N
        self.shape = input_shape
        self.batch_size = input_shape[0]
        
        Q = QFunction(input_shape, action_n, scope="Q")
        target_Q = QFunction(input_shape, action_n, scope="target_Q")

        # Forward Q
        self.s = tf.placeholder(shape=[None]+input_shape[1:], dtype=tf.float32)
        self.a = tf.placeholder(shape=[self.batch_size, 1], dtype=tf.int32)
        self.probs = Q(self.s)

        # add offset 
        first = tf.expand_dims(tf.range(self.batch_size), axis=1)
        indices = tf.concat(values=[first, self.a], concat_dim=1)

        # gather corresiponding q_vals
        self.q_val = tf.expand_dims(tf.gather_nd(self.probs, indices), axis=1)

        # TD target
        self.done = tf.placeholder(shape=[self.batch_size, 1], dtype=tf.float32)
        self.r = tf.placeholder(shape=[self.batch_size, 1], dtype=tf.float32)
        self.s_ = tf.placeholder(shape=input_shape, dtype=tf.float32)
        self.y = self.r + gamma*(1.0 - self.done)*tf.reduce_max(target_Q(self.s_), axis=1, keep_dims=True)

        # Error Clipping 
        self.loss = tf.reduce_mean(Hurber_loss(self.q_val, self.y))

        # Update Q
        opt = tf.train.RMSPropOptimizer(0.00025, 0.99, 0.0, 1e-6)
        grads_and_vars = opt.compute_gradients(self.loss)
        grads_and_vars = [[grad, var] for grad, var in grads_and_vars \
                          if grad is not None and var.name.startswith("Q")]
        self.train_op = opt.apply_gradients(grads_and_vars)
        
        # Update target Q
        self.target_train_op = copy_params(Q, target_Q)
        
        # replay buffer
        self.D = []
        
    def update_target(self, sess):
        _ = sess.run(self.target_train_op)
            
    def update(self, sess):
        # sample from replay buffer
        samples = random.sample(self.D, self.batch_size)
        s = np.asarray([sample[0] for sample in samples], dtype=np.float32)
        a = np.asarray([[sample[1]] for sample in samples], dtype=np.int32)
        r = np.asarray([[sample[2]] for sample in samples], dtype=np.float32)
        done = np.asarray([[sample[3]] for sample in samples], dtype=np.float32)
        s_ = np.asarray([sample[4] for sample in samples], dtype=np.float32)

        feed={self.s:s, self.a:a, self.r:r, self.done:done, self.s_:s_}
        _ = sess.run(self.train_op, feed_dict=feed)

    def greedy(self, s, sess):
        probs = sess.run( self.probs, feed_dict={self.s:s})
        return np.argmax(probs)
    
    def set_exp(self, exp):
        if len(self.D) <= self.N:
            self.D.append(exp)
        else:
            s, a, r, done, _ = self.D[0]            
            self.D = self.D[1:]
            self.D.append(exp)
            
            del s, a, r, done
                        
            
