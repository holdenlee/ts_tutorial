import numpy as np
import random as rnd
import time

#https://github.com/b2du/LangevinTS/blob/master/code/SAGALD.py

_LARGE_NUMBER = 1e+2

def evaluate_log1pexp(x):
    """given the input x, returns log(1+exp(x))."""
    return np.piecewise(x, [x>_LARGE_NUMBER], [lambda x: x, lambda x: np.log(1+np.exp(x))])
    """
    if x > _LARGE_NUMBER:
      return x
    else:
      return np.log(1+np.exp(x))
    """

# x : R^d
# data = (contexts : (R^d)^T, rewards : (R^d)^T)
def logistic_grad_f(x, data):
    zs = data[0]
    ys = data[1]
    m = -x.dot(zs.T)
    preds = np.piecewise(m, [m>_LARGE_NUMBER], [lambda x: 0, lambda x: 1/(1+np.exp(x))])
    #preds = 1/(1+np.exp(-x.dot(zs.T)))
    #print(np.shape(preds), np.shape(ys), np.shape(zs))
    grads = np.diag(preds - ys).dot(zs)
    return grads

class Gaussian_prior_grad_f(object):
    # mu : R^d
    # cov : Maybe (R^d)^d
    def __init__(self, mu, cov=None):
        d = np.shape(mu)[0]
        self.inv_cov = np.eye(d) if cov is None else np.linalg.inv(cov)
        self.mu = mu
    def __call__(self, x):
        #print(np.shape(x), np.shape(self.mu))
        return self.inv_cov.dot(x-self.mu)

def langevin_step(d, data, batch_grad_f, prior_grad_f, 
                  x, step_size = 0.01):
    grads = batch_grad_f(x, data)
    gradient = np.sum(grads, axis = 0)
    g = gradient
    g_prior = prior_grad_f(x)
    g = g + g_prior
    noise = np.random.randn(d)
    #preconditioner_sqrt.dot(np.random.randn(self.dim)) 
    x = x - step_size * g + \
        np.sqrt(2*step_size)*noise
    return x #, gradients, gradient

def langevin(d, data, batch_grad_f, prior_grad_f, 
             step_size = 0.01, n_steps=100, init_pt=None):
    if init_pt is None:
        init_pt = np.zeros(d)
    x = init_pt
    for t in range(n_steps):
        x = langevin_step(d, data, batch_grad_f, prior_grad_f, x, step_size)
    return x

# t : int
# d : int
# gradients : (R^d)^t
# gradient : R^d (sum of gradients)
# data : a (tuple of numpy arrays) 
    # todo - also generalize to numpy array - for example, (R^(d'))^t - or 
# batch_grad_f : (R^d) -> a -> (R^d)^(batch_size)
# prior_grad_f : R^d -> R^d
# x : R^d
# batch_size : int
# step_size : float
def sagald_step(t, d, gradients, gradient, data, batch_grad_f, prior_grad_f, 
                x, batch_size = 32, step_size = 0.01):
    if t <= batch_size:
      sample_indices = range(t)
      #gradient_scale = 1
    else:
      gradient_scale = t/batch_size
      sample_indices = rnd.sample(range(t),batch_size)
    
    old_gradients = gradients[sample_indices]
    sampled_data = tuple([arr[sample_indices] for arr in data])
    # ex. this is (zs, ys)
    #zs = self.contexts[sample_indices] # .T
    #ys = self.rewards[sample_indices]
    #to generalize to tuple of arrays OR array,
    #if isinstance(data, np.ndarray)
    
    #g is estimated gradient
    grads = batch_grad_f(x, sampled_data)
    if t <= batch_size:
        gradients[sample_indices] = grads
        gradient = np.sum(grads, axis = 0)
        g = gradient
    else:
        old_grad_sum = np.sum(gradients[sample_indices], axis=0)
        gradients[sample_indices] = grads #this mutates gradients!
        new_grad_sum = np.sum(grads, axis = 0)
        g = gradient + gradient_scale * (new_grad_sum - old_grad_sum) #variance-reduced gradient
        gradient = gradient + (new_grad_sum - old_grad_sum) 
            #warning, this doesn't mutate, need to do it in the calling method
    g_prior = prior_grad_f(x)
    #print(np.shape(g),np.shape(g_prior),'grad_shape')
    g = g + g_prior
    noise = np.random.randn(d)
    #preconditioner_sqrt.dot(np.random.randn(self.dim)) 
    x = x - step_size * g + \
        np.sqrt(2*step_size)*noise
    #print(x)
    return x, gradients, gradient

# t : int
# d : int
# data : a (tuple of numpy arrays) 
    # todo - also generalize to numpy array - for example, (R^(d'))^t - or 
# gradients : (R^d)^t
# gradient : R^d (sum of gradients)
# batch_grad_f : (R^d) -> a -> (R^d)^(batch_size)
# prior_grad_f : R^d -> R^d
# x : R^d
# batch_size : int
# step_size : float
# num_steps : int
# max_time : float (in seconds)
def sagald(t, d, data, batch_grad_f, prior_grad_f, 
           x = None, gradients = None, gradient = None,
           batch_size = 32, step_size = 0.01, num_steps = 200,
           max_time = 0.0):
    if x is None:
        x = np.zeros(d)
    if gradients is None:
        gradients = batch_grad_f(x, sampled_data)
    if gradient is None:
        gradient = np.sum(gradients, axis=0)
    for i in range(num_steps):
        (x, gradients, gradient) = \
             sagald_step(t, d, gradients, gradient, data, 
                         batch_grad_f, prior_grad_f, 
                         x, batch_size = batch_size, step_size = step_size)
    return x, gradients, gradient