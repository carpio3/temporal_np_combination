from __future__ import print_function

import tensorflow as tf
import numpy as np

from models.slim.nets.inception_resnet_v2 import inception_resnet_v2

from constants import *

MAX_BN_LEN = 250
CHECKPOINT = "inception_resnet_v2_2016_08_30.ckpt"

layer_elements = [-1, 16, 32, 128, 3]

output_sizes = [32, 16, 4]
filter_sizes = [4, 4, 8]
stride_sizes = [2, 2, 4]
padding_size = [1, 1, 2]

aud_layer_elements = [-1, 16, 32, 128, 3]

aud_output_sizes = [(32, 6), (16, 4), (4, 4)]
aud_filter_sizes = [(8, 3), (4, 3), (8, 3)]
aud_stride_sizes = [(4, 1), (2, 1), (4, 1)]
aud_padding_size = [(2, 0), (1, 0), (2, 1)]

slim = tf.contrib.slim

TOTAL_PARAMS = 3
num_params = 1


class DQNModel:
    # filename - saved model parameters
    def __init__(self, graphbuild=[1] * TOTAL_PARAMS, batch_size=1, filename="", name="dqn", learning_rate=1e-4,
                 log_dir=""):
        self.graphbuild = graphbuild
        self.__batch_size = batch_size
        self.__name = name
        self.__alpha = learning_rate
        self.log_dir = log_dir

        # variables
        def weight_variable(name, shape):
            initial = tf.truncated_normal(shape, stddev=0.1)
            return tf.Variable(initial, name=name)

        def bias_variable(name, shape):
            initial = tf.constant(0.1, shape=shape)
            return tf.Variable(initial, name=name)

        self.variables_pnt = {
            "W1": weight_variable("W_conv1_pnt",
                                  [filter_sizes[0], filter_sizes[0], pnt_dtype["num_c"], layer_elements[1]]),
            "b1": bias_variable("b_conv1_pnt", [layer_elements[1]]),
            "W2": weight_variable("W_conv2_pnt",
                                  [filter_sizes[1], filter_sizes[1], layer_elements[1], layer_elements[2]]),
            "b2": bias_variable("b_conv2_pnt", [layer_elements[2]]),
            "W3": weight_variable("W_conv3_pnt",
                                  [filter_sizes[2], filter_sizes[2], layer_elements[2], layer_elements[-2]]),
            "b3": bias_variable("b_conv3_pnt", [layer_elements[-2]])  # ,
        }

        self.variables_aud = {
            "W1": weight_variable("W_conv1_aud", [aud_filter_sizes[0][0], aud_filter_sizes[0][1], aud_dtype["num_c"],
                                                  aud_layer_elements[1]]),
            "b1": bias_variable("b_conv1_aud", [aud_layer_elements[1]]),
            "W2": weight_variable("W_conv2_aud", [aud_filter_sizes[1][0], aud_filter_sizes[1][1], aud_layer_elements[1],
                                                  aud_layer_elements[2]]),
            "b2": bias_variable("b_conv2_aud", [aud_layer_elements[2]]),
            "W3": weight_variable("W_conv3_aud", [aud_filter_sizes[2][0], aud_filter_sizes[2][1], aud_layer_elements[2],
                                                  aud_layer_elements[3]]),
            "b3": bias_variable("b_conv3_aud", [aud_layer_elements[3]])
        }

        self.variables_lstm = {
            # "W_lstm" : weight_variable("W_lstm", [4,layer_elements[-1]]),
            "W_lstm": weight_variable("W_lstm", [layer_elements[-2], layer_elements[-1]]),
            "b_lstm": bias_variable("b_lstm", [layer_elements[-1]]),
            "W_fc": weight_variable("W_fc", [layer_elements[-1], layer_elements[-1]]),
            "b_fc": bias_variable("b_fc", [layer_elements[-1]])
        }

        self.variables_pnt_hat = {
            "W1": weight_variable("W_conv1_pnt_hat",
                                  [filter_sizes[0], filter_sizes[0], pnt_dtype["num_c"], layer_elements[1]]),
            "b1": bias_variable("b_conv1_pnt_hat", [layer_elements[1]]),
            "W2": weight_variable("W_conv2_pnt_hat",
                                  [filter_sizes[1], filter_sizes[1], layer_elements[1], layer_elements[2]]),
            "b2": bias_variable("b_conv2_pnt_hat", [layer_elements[2]]),
            "W3": weight_variable("W_conv3_pnt_hat",
                                  [filter_sizes[2], filter_sizes[2], layer_elements[2], layer_elements[-2]]),
            "b3": bias_variable("b_conv3_pnt_hat", [layer_elements[-2]])  # ,
        }

        self.variables_aud_hat = {
            "W1": weight_variable("W_conv1_aud_hat",
                                  [aud_filter_sizes[0][0], aud_filter_sizes[0][1], aud_dtype["num_c"],
                                   aud_layer_elements[1]]),
            "b1": bias_variable("b_conv1_aud_hat", [aud_layer_elements[1]]),
            "W2": weight_variable("W_conv2_aud_hat",
                                  [aud_filter_sizes[1][0], aud_filter_sizes[1][1], aud_layer_elements[1],
                                   aud_layer_elements[2]]),
            "b2": bias_variable("b_conv2_aud_hat", [aud_layer_elements[2]]),
            "W3": weight_variable("W_conv3_aud_hat",
                                  [aud_filter_sizes[2][0], aud_filter_sizes[2][1], aud_layer_elements[2],
                                   aud_layer_elements[3]]),
            "b3": bias_variable("b_conv3_aud_hat", [aud_layer_elements[3]])
        }

        self.variables_lstm_hat = {
            "W_lstm": weight_variable("W_lstm_hat", [layer_elements[-2], layer_elements[-1]]),
            "b_lstm": bias_variable("b_lstm_hat", [layer_elements[-1]]),
            "W_fc": weight_variable("W_fc_hat", [layer_elements[-1], layer_elements[-1]]),
            "b_fc": bias_variable("b_fc_hat", [layer_elements[-1]])
        }

        # placeholders
        self.img_ph = tf.placeholder("float",
                                     [self.__batch_size, None,
                                      img_dtype["cmp_h"] * img_dtype["cmp_w"] * img_dtype["num_c"]],
                                     name="img_placeholder")

        self.pnt_ph = tf.placeholder("float",
                                     [self.__batch_size, None,
                                      pnt_dtype["cmp_h"] * pnt_dtype["cmp_w"] * pnt_dtype["num_c"]],
                                     name="pnt_placeholder")
        self.aud_ph = tf.placeholder("float",
                                     [self.__batch_size, None,
                                      aud_dtype["cmp_h"] * aud_dtype["cmp_w"] * aud_dtype["num_c"]],
                                     name="aud_placeholder")
        self.seq_length_ph = tf.placeholder("int32", [self.__batch_size], name="seq_len_placeholder")
        self.partitions_ph = tf.placeholder("int32", [self.__batch_size, None], name="partition_placeholder")
        self.train_ph = tf.placeholder("bool", [], name="train_placeholder")
        self.prompts_ph = tf.placeholder("float32", [self.__batch_size], name="prompts_placeholder")

        self.y_ph = tf.placeholder("float", [None, layer_elements[-1]], name="y_placeholder")

        # model
        self.pred_var_set = self.execute_model_DQN_var_set()  # used to initialize variables
        self.pred = self.execute_model_DQN()  # used for training
        self.pred_hat = self.execute_model_DQN_hat()  # used to evaluate q_hat
        self.max_q_hat = tf.reduce_max(self.pred_hat, axis=1)
        self.pred_index = tf.argmax(self.pred, 1)
        # inception variables
        self.variables_img = {}

        exclusions = ["InceptionResnetV2/Logits", "InceptionResnetV2/AuxLogits"]

        variables_to_restore = []
        if (self.graphbuild[0]):
            for var in slim.get_model_variables():
                excluded = False
                for exclusion in exclusions:
                    if var.op.name.startswith(exclusion):
                        name = var.name[var.name.find('/') + 1:-2]
                        self.variables_img[name] = var
                        excluded = True
                        break

                if not excluded:
                    variables_to_restore.append(var)

            slim.assign_from_checkpoint_fn(
                CHECKPOINT,
                variables_to_restore)

        variables_to_train = [x for x in tf.trainable_variables() if x not in variables_to_restore]

        self.variables_img_main = {}
        self.variables_img_hat = {}
        for k in self.variables_img.keys():
            self.variables_img_main[k] = tf.Variable(self.variables_img[k].initialized_value())
            self.variables_img_hat[k] = tf.Variable(self.variables_img[k].initialized_value())

        self.diff = self.y_ph - tf.clip_by_value(self.pred, 1e-10, 100)

        self.cross_entropy = tf.reduce_mean(tf.square(self.diff))
        # self.cross_entropy = -tf.reduce_sum(self.y_ph*tf.log(tf.clip_by_value(self.pred,1e-10,1.0)))
        tf.summary.scalar('cross_entropy', self.cross_entropy)
        self.optimizer = tf.train.AdamOptimizer(learning_rate=self.__alpha).minimize(self.cross_entropy,
                                                                                     var_list=variables_to_train)

        self.correct_pred = tf.equal(tf.argmax(self.pred, 1), tf.argmax(self.y_ph, 1))
        self.accuracy = tf.reduce_mean(tf.cast(self.correct_pred, tf.float32))
        tf.summary.scalar('accuracy', self.accuracy)

        self.predict_output = tf.argmax(self.pred, 1)

        # session
        self.sess = tf.InteractiveSession(config=tf.ConfigProto(allow_soft_placement=True))

        self.saver = tf.train.Saver()

        self.merged_summary = tf.summary.merge_all()
        self.train_writer = tf.summary.FileWriter(self.log_dir + '/train', self.sess.graph)
        self.test_writer = tf.summary.FileWriter(self.log_dir + '/test')
        self.graph_writer = tf.summary.FileWriter(self.log_dir + '/projector', self.sess.graph)

        if (len(filename) == 0):
            init_op = tf.global_variables_initializer()
            self.sess.run(init_op)  # remove when using a saved file
        else:
            print("RESTORING VALUES")
            self.saver.restore(self.sess, filename)

    def saveModel(self, name="model.ckpt", save_dir=""):
        path = self.saver.save(self.sess, save_dir + '/' + name)

    def restore_q_hat_vars(self, src, dst):
        arr = []
        var_dst = []
        for k in dst.keys():
            arr.append(src[k])
            var_dst.append(dst[k])
        arr = self.sess.run(arr)
        for seq, var in zip(arr, var_dst):
            v = np.array(seq).reshape(np.array(seq).shape)
            var.load(v, session=self.sess)

    def assignVariables(self):
        # for the inception network variables
        self.restore_q_hat_vars(self.variables_img_main, self.variables_img_hat)

        # for all other network variables
        self.restore_q_hat_vars(self.variables_pnt, self.variables_pnt_hat)
        self.restore_q_hat_vars(self.variables_aud, self.variables_aud_hat)
        self.restore_q_hat_vars(self.variables_lstm, self.variables_lstm_hat)

    def genPrediction(self, num_frames, img_data, pnt_data, aud_data, num_prompts):
        # used by the ASD robot
        partitions = np.zeros((1, num_frames))
        print("partitions.shape: ", partitions.shape)
        partitions[0][-1] = 1
        print("num_prompts: ", num_prompts)
        with tf.variable_scope(self.__name) as scope:
            prediction = self.sess.run(self.pred, feed_dict={  # generate_pred
                self.seq_length_ph: [num_frames],
                self.img_ph: img_data,
                self.pnt_ph: pnt_data,
                self.aud_ph: aud_data,
                self.partitions_ph: partitions,
                self.train_ph: False,
                self.prompts_ph: [num_prompts]
            })
            print(prediction, np.max(prediction), np.argmax(prediction))
            return np.argmax(prediction)  # prediction[0]

    def execute_model_DQN_var_set(self):
        return self.model(self.seq_length_ph,
                          self.img_ph,
                          self.pnt_ph,
                          self.aud_ph,
                          self.partitions_ph,
                          self.train_ph,
                          self.prompts_ph,
                          tf.variable_scope("dqn"),
                          tf.variable_scope("dqn"),
                          "",
                          self.variables_pnt,
                          self.variables_aud,
                          self.variables_lstm,
                          False
                          )

    def execute_model_DQN(self):
        return self.model(self.seq_length_ph,
                          self.img_ph,
                          self.pnt_ph,
                          self.aud_ph,
                          self.partitions_ph,
                          self.train_ph,
                          self.prompts_ph,
                          tf.variable_scope("dqn"),
                          tf.variable_scope("dqn", reuse=True),
                          "",
                          self.variables_pnt,
                          self.variables_aud,
                          self.variables_lstm
                          )

    def execute_model_DQN_hat(self):
        return self.model(self.seq_length_ph,
                          self.img_ph,
                          self.pnt_ph,
                          self.aud_ph,
                          self.partitions_ph,
                          self.train_ph,
                          self.prompts_ph,
                          tf.variable_scope("dqn_hat"),
                          tf.variable_scope("dqn", reuse=True),
                          "",
                          self.variables_pnt_hat,
                          self.variables_aud_hat,
                          self.variables_lstm_hat
                          )

    def variable_summaries(self, var, name):
        """Attach a lot of summaries to a Tensor (for TensorBoard visualization)."""
        with tf.name_scope('summaries' + name):
            mean = tf.reduce_mean(var)
            tf.summary.scalar('mean', mean)
            with tf.name_scope('stddev'):
                stddev = tf.sqrt(tf.reduce_mean(tf.square(var - mean)))
            tf.summary.scalar('stddev', stddev)
            tf.summary.scalar('max', tf.reduce_max(var))
            tf.summary.scalar('min', tf.reduce_min(var))
            tf.summary.histogram('histogram', var)

        #####################
        ##### THE MODEL #####
        #####################

    def model(self, seq_length, img_ph, pnt_ph, aud_ph, partitions_ph, train_ph, prompts_ph, variable_scope,
              variable_scope2, var_img, var_pnt, var_aud, var_lstm, incep_reuse=True):  #
        def process_vars(seq, data_type):
            # cast inputs to the correct data type
            seq_inp = tf.cast(seq, tf.float32)
            return tf.reshape(seq_inp,
                              (self.__batch_size, -1, data_type["cmp_h"], data_type["cmp_w"], data_type["num_c"]))

        def convolve_data_inception(input_data, val, n, dtype):
            data = tf.reshape(input_data, [-1, 299, 299, 3])
            logits, end_points = inception_resnet_v2(data,
                                                     num_classes=output_sizes[-1] * output_sizes[-1] * layer_elements[
                                                         -2], is_training=False, reuse=incep_reuse)
            return logits

        def convolve_data_3layer_pnt(input_data, val, variables, n, dtype):
            def pad_tf(x, p):
                return tf.pad(x, [[0, 0], [p, p], [p, p], [0, 0]], "CONSTANT")

            def gen_convolved_output(sequence, W, b, stride, num_hidden, new_size, train_ph, padding='SAME'):
                conv = tf.nn.conv2d(sequence, W, strides=[1, stride, stride, 1], padding=padding) + b
                return tf.nn.relu(conv)

            input_data = tf.reshape(input_data, [-1, dtype["cmp_h"], dtype["cmp_w"], dtype["num_c"]],
                                    name=n + "_inp_reshape")

            # input_data = tf.Print(input_data, [tf.shape(input_data)], message="out1_n: ")
            input_data = pad_tf(input_data, padding_size[0])
            padding = "VALID"

            input_data = gen_convolved_output(input_data, variables["W1"], variables["b1"], stride_sizes[0],
                                              layer_elements[1], output_sizes[0], train_ph, padding)
            self.variable_summaries(input_data, dtype["name"] + "_conv1")
            input_data = tf.verify_tensor_all_finite(
                input_data,
                "ERR: Tensor not finite - ",
                name="conv1_" + n
            )

            # input_data = tf.Print(input_data, [tf.shape(input_data)], message="out2_n: ")
            input_data = pad_tf(input_data, padding_size[1])
            padding = "VALID"

            input_data = gen_convolved_output(input_data, variables["W2"], variables["b2"], stride_sizes[1],
                                              layer_elements[2], output_sizes[1], train_ph, padding)
            self.variable_summaries(input_data, dtype["name"] + "_conv2")
            input_data = tf.verify_tensor_all_finite(
                input_data,
                "ERR: Tensor not finite - ",
                name="conv2_" + n
            )

            # input_data = tf.Print(input_data, [tf.shape(input_data)], message="out3_n: ")
            input_data = pad_tf(input_data, padding_size[2])
            padding = "VALID"

            input_data = gen_convolved_output(input_data, variables["W3"], variables["b3"], stride_sizes[-1],
                                              layer_elements[-2], output_sizes[-1], train_ph, padding)
            self.variable_summaries(input_data, dtype["name"] + "_conv3")
            input_data = tf.verify_tensor_all_finite(
                input_data,
                "ERR: Tensor not finite - ",
                name="conv3_" + n
            )

            # input_data = tf.Print(input_data, [tf.shape(input_data)], message="out4_n: ")

            return input_data

        def convolve_data_3layer_aud(input_data, val, variables, n, dtype):
            def pad_tf(x, padding):
                return tf.pad(x, [[0, 0], [padding[0], padding[0]], [padding[1], padding[1]], [0, 0]], "CONSTANT")

            def gen_convolved_output(sequence, W, b, stride, num_hidden, new_size, train_ph, padding='SAME'):
                conv = tf.nn.conv2d(sequence, W, strides=[1, stride[0], stride[1], 1], padding=padding) + b
                return tf.nn.relu(conv)

            input_data = tf.reshape(input_data, [-1, dtype["cmp_h"], dtype["cmp_w"], dtype["num_c"]],
                                    name=n + "_inp_reshape")

            # input_data = tf.Print(input_data, [tf.shape(input_data)], message="out1_a: ")
            input_data = pad_tf(input_data, aud_padding_size[0])
            padding = "VALID"

            input_data = gen_convolved_output(input_data, variables["W1"], variables["b1"], aud_stride_sizes[0],
                                              aud_layer_elements[1], aud_output_sizes[0], train_ph, padding)
            self.variable_summaries(input_data, dtype["name"] + "_conv1")
            input_data = tf.verify_tensor_all_finite(
                input_data,
                "ERR: Tensor not finite - conv1_" + n,
                name="conv1_" + n
            )

            # input_data = tf.Print(input_data, [tf.shape(input_data)], message="out2_a: ")
            input_data = pad_tf(input_data, aud_padding_size[1])
            padding = "VALID"

            input_data = gen_convolved_output(input_data, variables["W2"], variables["b2"], aud_stride_sizes[1],
                                              aud_layer_elements[2], aud_output_sizes[1], train_ph, padding)
            self.variable_summaries(input_data, dtype["name"] + "_conv2")
            input_data = tf.verify_tensor_all_finite(
                input_data,
                "ERR: Tensor not finite - conv2_" + n,
                name="conv2_" + n
            )

            # input_data = tf.Print(input_data, [tf.shape(input_data)], message="out3_a: ")
            input_data = pad_tf(input_data, aud_padding_size[2])
            padding = "VALID"

            input_data = gen_convolved_output(input_data, variables["W3"], variables["b3"], aud_stride_sizes[2],
                                              aud_layer_elements[3], aud_output_sizes[2], train_ph, padding)
            self.variable_summaries(input_data, dtype["name"] + "_conv3")
            input_data = tf.verify_tensor_all_finite(
                input_data,
                "ERR: Tensor not finite - conv3_" + n,
                name="conv3_" + n
            )

            return input_data

        # pass different data types through conv networks
        inp_data = [0] * TOTAL_PARAMS
        conv_inp = [0] * TOTAL_PARAMS

        # with tf.device('/gpu:0'):
        with tf.device('/gpu:1'):
            if (self.graphbuild[0]):
                val = 0
                inp_data[val] = process_vars(img_ph, img_dtype)
                conv_inp[val] = convolve_data_inception(inp_data[val], val, "img", img_dtype)

            with variable_scope as scope:
                # with tf.device('/gpu:1'):

                if (self.graphbuild[1]):
                    val = 1
                    inp_data[val] = process_vars(pnt_ph, pnt_dtype)
                    conv_inp[val] = convolve_data_3layer_pnt(inp_data[val], val, var_pnt, "pnt", pnt_dtype)
                if (self.graphbuild[2]):
                    val = 2
                    inp_data[val] = process_vars(aud_ph, aud_dtype)
                    conv_inp[val] = convolve_data_3layer_aud(inp_data[val], val, var_aud, "aud", aud_dtype)

                # combine different inputs together
                combined_data = None
                for i in range(TOTAL_PARAMS):

                    if (self.graphbuild[i]):
                        tf.Print(conv_inp[i], [tf.shape(conv_inp[i])])
                        if (i < 2):
                            conv_inp[i] = tf.reshape(conv_inp[i], [self.__batch_size, -1,
                                                                   output_sizes[-1] * output_sizes[-1] * layer_elements[
                                                                       -2]], name="combine_reshape")
                        else:
                            # print(">>", aud_output_sizes[-1][0]*aud_output_sizes[-1][0]*aud_layer_elements[-2])
                            conv_inp[i] = tf.reshape(conv_inp[i], [self.__batch_size, -1,
                                                                   aud_output_sizes[-1][0] * aud_output_sizes[-1][0] *
                                                                   aud_layer_elements[-2]], name="combine_reshape_aud")
                        # tf.Print(conv_inp[i], [tf.shape(conv_inp[i])])
                        if (combined_data == None):
                            combined_data = conv_inp[i]
                        else:
                            combined_data = tf.concat([combined_data, conv_inp[i]], 2)

                W_lstm = var_lstm["W_lstm"]
                b_lstm = var_lstm["b_lstm"]
                W_fc = var_lstm["W_fc"]
                b_fc = var_lstm["b_fc"]

                combined_data = tf.verify_tensor_all_finite(
                    combined_data,
                    "ERR: Tensor not finite - combined_data",
                    name="combined_data"
                )
            # combined_data = tf.Print(combined_data, [tf.shape(combined_data)], message="combined_data")

        with variable_scope2 as scope:
            # lstm_cell = BNLSTMCell(layer_elements[-2], is_training_tensor=train_ph, max_bn_steps=MAX_BN_LEN)

            lstm_cell = tf.contrib.rnn.LSTMCell(layer_elements[-2],
                                                use_peepholes=False,
                                                cell_clip=None,
                                                initializer=None,
                                                num_proj=None,
                                                proj_clip=None,
                                                forget_bias=1.0,
                                                state_is_tuple=True,
                                                activation=None,
                                                reuse=None
                                                )

            outputs, states = tf.nn.dynamic_rnn(
                cell=lstm_cell,
                inputs=combined_data,
                dtype=tf.float32,
                sequence_length=seq_length,
                time_major=False
            )

            outputs = tf.where(tf.is_nan(outputs), tf.zeros_like(outputs), outputs)
            # outputs = tf.Print(outputs, [outputs], message="outputs", summarize=100)
            # outputs = tf.Print(outputs, [tf.reduce_max(outputs)], message="outputs", summarize=100)
            outputs = tf.verify_tensor_all_finite(
                outputs,
                "ERR: Tensor not finite - outputs",
                name="outputs"
            )

            num_partitions = 2
            res_out = tf.dynamic_partition(outputs, partitions_ph, num_partitions)[1]
            # res_out = tf.Print(res_out, [res_out], message="res_out")

            # tf.where(tf.is_nan(res_out), tf.zeros_like(res_out), res_out)

            # res_out = tf.Print(res_out, [res_out], message="res_out", summarize=100)
            # res_out = tf.Print(res_out, [tf.reduce_max(res_out)], message="res_out", summarize=100)


            rnn_x = tf.matmul(res_out, W_lstm) + b_lstm

            self.variable_summaries(rnn_x, "lstm")

            rnn_x = tf.verify_tensor_all_finite(
                rnn_x,
                "ERR: Tensor not finite - fc1",
                name="fc1"
            )

            # prompts_ph = tf.reshape(prompts_ph, [-1, 1])
            x_tensor = rnn_x  # tf.concat([rnn_x, prompts_ph], 1)

            rnn_x = tf.matmul(x_tensor, W_fc) + b_fc
            self.variable_summaries(rnn_x, "fc")

            rnn_x = tf.verify_tensor_all_finite(
                rnn_x,
                "ERR: Tensor not finite - fc2",
                name="fc2"
            )

            return rnn_x


if __name__ == '__main__':
    dqn = DQNModel([1, 0, 0])
