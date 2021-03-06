
OLD_CHECKPOINT_FILE = "/Users/kartik/im2txt_2/im2txt_2016_10_11.2000000/model.ckpt-2000000"
NEW_CHECKPOINT_FILE = "/Users/kartik/im2txt_2/im2txt_2016_10_11.2000000/model.ckpt-2000000_renamed"

import tensorflow as tf
vars_to_rename = {
    "lstm/BasicLSTMCell/Linear/Matrix": "lstm/basic_lstm_cell/kernel",
    "lstm/BasicLSTMCell/Linear/Bias": "lstm/basic_lstm_cell/bias",
}
new_checkpoint_vars = {}
reader = tf.train.NewCheckpointReader(OLD_CHECKPOINT_FILE)
for old_name in reader.get_variable_to_shape_map():
  if old_name in vars_to_rename:
    new_name = vars_to_rename[old_name]
    print("renaming '" + old_name + "' to '" + new_name + "'")
  else:
    new_name = old_name
  new_checkpoint_vars[new_name] = tf.Variable(reader.get_tensor(old_name))

init = tf.global_variables_initializer()
saver = tf.train.Saver(new_checkpoint_vars)

with tf.Session() as sess:
  sess.run(init)
  saver.save(sess, NEW_CHECKPOINT_FILE)