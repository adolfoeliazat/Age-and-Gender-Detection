#code: UTF-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import sys
reload(sys)
#sys.setdefaultencoding('utf-8')
from datetime import datetime
import math
import time
from data import inputs
import numpy as np
import tensorflow as tf
from model import select_model, get_checkpoint
from utils import ImageCoder, make_batch
import os
import csv
import random

RESIZE_FINAL = 227
GENDER_LIST =['M','F']
AGE_LIST = ['(0, 2)','(4, 6)','(8, 12)','(15, 20)','(25, 32)','(38, 43)','(48, 53)','(60, 100)']
AGE_MODEL_PATH = '/Users/apple/Desktop/try/age_model'
GENDER_MODEL_PATH = '/Users/apple/Desktop/try/gender_model'
model_checkpoint_path = ''

tf.app.flags.DEFINE_string('model_dir', '',
                           'Model directory (where training data lives)')

tf.app.flags.DEFINE_string('class_type', 'age',
                           'Classification type (age|gender)')


tf.app.flags.DEFINE_string('device_id', '/cpu:0',
                           'What processing unit to execute inference on')

tf.app.flags.DEFINE_string('filename', '',
                           'File (Image) or File list (Text/No header TSV) to process')

tf.app.flags.DEFINE_string('target', '',
                           'CSV file containing the filename processed along with best guess and score')

tf.app.flags.DEFINE_string('checkpoint', 'checkpoint',
                          'Checkpoint basename')

tf.app.flags.DEFINE_string('model_type', 'default',
                           'Type of convnet')

tf.app.flags.DEFINE_string('requested_step', '', 'Within the model directory, a requested step to restore e.g., 9000')

tf.app.flags.DEFINE_boolean('single_look', False, 'single look at the image or multiple crops')

tf.app.flags.DEFINE_string('face_detection_model', '', 'Do frontal face detection with model specified')

FLAGS = tf.app.flags.FLAGS

def one_of(fname, types):
    for ty in types:
        if fname.endswith('.' + ty):
            return True
    return False

def resolve_file(fname):
    if os.path.exists(fname): return fname
    for suffix in ('.jpg', '.png', '.JPG', '.PNG', '.jpeg'):
        cand = fname + suffix
        if os.path.exists(cand):
            return cand
    return None

def classify(sess, label_list, softmax_output, coder, images, image_file):

    print('Running file %s' % image_file)
    image_batch = make_batch(image_file, coder, not FLAGS.single_look)
    batch_results = sess.run(softmax_output, feed_dict={images:image_batch.eval()})
    output = batch_results[0]
    batch_sz = batch_results.shape[0]
    for i in range(1, batch_sz):
        output = output + batch_results[i]

    output /= batch_sz
    best = np.argmax(output)
    best_choice = (label_list[best], output[best])
    print('Guess @ 1 %s, prob = %.2f' % best_choice)

    #calculate face score
    score = scoreAge(output)

    nlabels = len(label_list)
    if nlabels > 2:
        output[best] = 0
        second_best = np.argmax(output)

        print('Guess @ 2 %s, prob = %.2f' % (label_list[second_best], output[second_best]))
    return label_list[best],score

def classifyGender(sess, label_list, softmax_output, coder, images, image_file):

    print('Running file %s' % image_file)
    image_batch = make_batch(image_file, coder, not FLAGS.single_look)
    batch_results = sess.run(softmax_output, feed_dict={images:image_batch.eval()})
    output = batch_results[0]
    batch_sz = batch_results.shape[0]
    for i in range(1, batch_sz):
        output = output + batch_results[i]

    output /= batch_sz
    best = np.argmax(output)
    best_choice = (label_list[best], output[best])
    print('Guess @ 1 %s, prob = %.2f' % best_choice)

    #calculate face score
    #score = scoreAge(output)

    nlabels = len(label_list)
    if nlabels > 2:
        output[best] = 0
        second_best = np.argmax(output)

        print('Guess @ 2 %s, prob = %.2f' % (label_list[second_best], output[second_best]))
    return label_list[best]

def scoreAge(prop_list):
    #['(0, 2)', '(4, 6)', '(8, 12)', '(15, 20)', '(25, 32)', '(38, 43)', '(48, 53)', '(60, 100)']
    #[90, 80, 80, 70, 60, 50, 40, 20]
    score_list = [100, 100, 95, 90, 80, 50, 40, 20]
    random_score_list = []
    finalScore = 0
    for score in score_list:
        randScore = score + random.random() * 10
        random_score_list.append(randScore)
    j = 0
    while(j < len(random_score_list)):
        prop = prop_list[j]
        score = random_score_list[j]
        finalScore = finalScore + score * prop
        j = j + 1
    return finalScore

def batchlist(srcfile):
    with open(srcfile, 'r') as csvfile:
        reader = csv.reader(csvfile)
        if srcfile.endswith('.csv') or srcfile.endswith('.tsv'):
            print('skipping header')
            reader.next()

        return [row[0] for row in reader]

# def detectface(filename):
#     files = []
#     #print('Using face detector %s' % FLAGS.face_detection_model)
#     face_detect = FaceDetector('haarcascade_frontalface_default.xml')
#     face_files, rectangles = face_detect.run(filename)
#     files += face_files
#     if (len(files)>0) :
#         return 1
#     else:
#         return 0

def guessAge(image_file):

    #import!!!Fix the bug http://stackoverflow.com/questions/33765336/remove-nodes-from-graph-or-reset-entire-default-graph
    tf.reset_default_graph()
    with tf.Session() as sess:

        age_label_list = AGE_LIST
        agelabels = len(age_label_list)

        # print('Executing on %s' % FLAGS.device_id)
        model_fn = select_model('inception')

        images = tf.placeholder(tf.float32, [None, RESIZE_FINAL, RESIZE_FINAL, 3])
        logits_age = model_fn(agelabels, images, 1, False)
        init = tf.global_variables_initializer()

        requested_step = FLAGS.requested_step if FLAGS.requested_step else None

        checkpoint_path = '%s' % (AGE_MODEL_PATH)
        # update in 0.11 version

        model_checkpoint_path, global_step = get_checkpoint(checkpoint_path, requested_step, FLAGS.checkpoint)
    #print 'model_checkpoint_path is', model_checkpoint_path
        #print model_checkpoint_path
    saver = tf.train.Saver()
    if not saver.last_checkpoints :
        saver.restore(sess, model_checkpoint_path)


    softmax_output = tf.nn.softmax(logits_age)

    coder = ImageCoder()

    files = []

    # detect age
    best_choice = classify(sess, age_label_list, softmax_output, coder, images, image_file)

    sess.close()
    return best_choice

def guessGender(image_file):
    tf.reset_default_graph()
    with tf.Session() as sess:

        #sess = tf.Session()
        age_label_list = AGE_LIST
        gender_label_list = GENDER_LIST
        genderlabels = len(gender_label_list)

        # print('Executing on %s' % FLAGS.device_id)
        model_fn = select_model('')

        with tf.device(FLAGS.device_id):

            images = tf.placeholder(tf.float32, [None, RESIZE_FINAL, RESIZE_FINAL, 3])
            logits_gender = model_fn(genderlabels, images, 1, False)
            init = tf.global_variables_initializer()

            requested_step = FLAGS.requested_step if FLAGS.requested_step else None

            checkpoint_path = '%s' % (GENDER_MODEL_PATH)

            model_checkpoint_path, global_step = get_checkpoint(checkpoint_path, requested_step, FLAGS.checkpoint)

            saver = tf.train.Saver()
            saver.restore(sess, model_checkpoint_path)

            softmax_output = tf.nn.softmax(logits_gender)

            coder = ImageCoder()

            files = []

            # detect gender
            #try:
            best_choice = classifyGender(sess, gender_label_list, softmax_output, coder, images, image_file)
            return best_choice
            #except Exception as e:
            #    print(e)
            #    print('Failed to run image %s ' % image_file)