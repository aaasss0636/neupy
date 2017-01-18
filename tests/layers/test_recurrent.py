import numpy as np
from sklearn.model_selection import train_test_split

from neupy.exceptions import LayerConnectionError
from neupy.datasets import reber
from neupy import layers, algorithms

from base import BaseTestCase


def add_padding(data):
    n_sampels = len(data)
    max_seq_length = max(map(len, data))

    data_matrix = np.zeros((n_sampels, max_seq_length))
    for i, sample in enumerate(data):
        data_matrix[i, -len(sample):] = sample

    return data_matrix


class LSTMTestCase(BaseTestCase):
    def setUp(self):
        super(LSTMTestCase, self).setUp()

        data, labels = reber.make_reber_classification(
            n_samples=100, return_indeces=True)
        data = add_padding(data + 1)  # +1 to shift indeces

        # self.data = x_train, x_test, y_train, y_test
        self.data = train_test_split(data, labels, train_size=0.8)

        self.n_categories = len(reber.avaliable_letters) + 1
        self.n_time_steps = self.data[0].shape[1]

    def train_lstm(self, data, **lstm_options):
        x_train, x_test, y_train, y_test = data
        network = algorithms.RMSProp(
            [
                layers.Input(self.n_time_steps),
                layers.Embedding(self.n_categories, 10),
                layers.LSTM(20, **lstm_options),
                layers.Sigmoid(1),
            ],

            step=0.05,
            verbose=False,
            batch_size=16,
            error='binary_crossentropy',
        )
        network.train(x_train, y_train, x_test, y_test, epochs=20)

        y_predicted = network.predict(x_test).round()
        accuracy = (y_predicted.T == y_test).mean()
        return accuracy

    def test_simple_lstm_sequence_classification(self):
        accuracy = self.train_lstm(self.data)
        self.assertGreaterEqual(accuracy, 0.95)

    def test_simple_lstm_without_precomputed_input(self):
        accuracy = self.train_lstm(self.data, precompute_input=False)
        self.assertGreaterEqual(accuracy, 0.95)

    def test_lstm_with_gradient_clipping(self):
        accuracy = self.train_lstm(self.data, gradient_clipping=1)
        self.assertGreaterEqual(accuracy, 0.95)

    def test_lstm_with_enabled_peepholes_option(self):
        accuracy = self.train_lstm(self.data, peepholes=True)
        self.assertGreaterEqual(accuracy, 0.95)

    def test_lstm_with_enabled_unroll_scan_option(self):
        accuracy = self.train_lstm(self.data, unroll_scan=True)
        self.assertGreaterEqual(accuracy, 0.95)

    def test_lstm_with_enabled_backwards_option(self):
        x_train, x_test, y_train, y_test = self.data
        x_train = x_train[:, ::-1]
        x_test = x_test[:, ::-1]

        data = x_train, x_test, y_train, y_test
        accuracy = self.train_lstm(data, backwards=True)
        self.assertGreaterEqual(accuracy, 0.95)

        accuracy = self.train_lstm(data, backwards=True, unroll_scan=True)
        self.assertGreaterEqual(accuracy, 0.95)

    def test_lstm_output_shapes(self):
        network_1 = layers.join(
            layers.Input((10, 2)),
            layers.LSTM(20, only_return_final=True),
        )
        self.assertEqual(network_1.output_shape, (20,))

        network_2 = layers.join(
            layers.Input((10, 2)),
            layers.LSTM(20, only_return_final=False),
        )
        self.assertEqual(network_2.output_shape, (10, 20))

    def test_stacked_lstm(self):
        x_train, x_test, y_train, y_test = self.data
        network = algorithms.RMSProp(
            [
                layers.Input(self.n_time_steps),
                layers.Embedding(self.n_categories, 10),
                layers.LSTM(10, only_return_final=False),
                layers.LSTM(2),
                layers.Sigmoid(1),
            ],

            step=0.1,
            verbose=False,
            batch_size=1,
            error='binary_crossentropy',
        )
        network.train(x_train, y_train, x_test, y_test, epochs=20)

        y_predicted = network.predict(x_test).round()
        accuracy = (y_predicted.T == y_test).mean()

        self.assertGreaterEqual(accuracy, 0.95)

    def test_stacked_lstm_with_enabled_backwards_option(self):
        x_train, x_test, y_train, y_test = self.data
        x_train = x_train[:, ::-1]
        x_test = x_test[:, ::-1]

        network = algorithms.RMSProp(
            [
                layers.Input(self.n_time_steps),
                layers.Embedding(self.n_categories, 10),
                layers.LSTM(10, only_return_final=False, backwards=True),
                layers.LSTM(2, backwards=True),
                layers.Sigmoid(1),
            ],

            step=0.1,
            verbose=False,
            batch_size=1,
            error='binary_crossentropy',
        )
        network.train(x_train, y_train, x_test, y_test, epochs=20)

        y_predicted = network.predict(x_test).round()
        accuracy = (y_predicted.T == y_test).mean()

        self.assertGreaterEqual(accuracy, 0.9)

    def test_lstm_with_4d_input(self):
        x_train, x_test, y_train, y_test = self.data
        network = algorithms.RMSProp(
            [
                layers.Input(self.n_time_steps),
                layers.Embedding(self.n_categories, 10),
                # Make 4D input
                layers.Reshape((self.n_time_steps, 5, 2), name='reshape'),
                layers.LSTM(10),
                layers.Sigmoid(1),
            ],

            step=0.1,
            verbose=False,
            batch_size=1,
            error='binary_crossentropy',
        )
        network.train(x_train, y_train, x_test, y_test, epochs=2)

        reshape = network.connection.end('reshape')
        # +1 for batch size
        output_dimension = len(reshape.output_shape) + 1
        self.assertEqual(4, output_dimension)

    def test_lstm_connection_exceptions(self):
        with self.assertRaises(LayerConnectionError):
            layers.Input(1) > layers.LSTM(10)