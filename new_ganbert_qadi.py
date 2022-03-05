
# !pip install transformers==4.3.2
import torch
import io
import torch.nn.functional as F
import random
import numpy as np
import time
import math
import datetime
import torch.nn as nn
from transformers import *
from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
#!pip install torch==1.7.1+cu101 torchvision==0.8.2+cu101 -f https://download.pytorch.org/whl/torch_stable.html
#!pip install sentencepiece

file = open("out.txt", "w")

##Set random values
seed_val = 42
random.seed(seed_val)
np.random.seed(seed_val)
torch.manual_seed(seed_val)
if torch.cuda.is_available():
  torch.cuda.manual_seed_all(seed_val)

# If there's a GPU available... 
if torch.cuda.is_available():    
    # Tell PyTorch to use the GPU.    
    device = torch.device("cuda")
    file.write('There are %d GPU(s) available.' % torch.cuda.device_count())
    file.write("\n")
    file.write('We will use the GPU:'+ torch.cuda.get_device_name(0))
    file.write("\n")
# If not...
else:
    file.write('No GPU available, using the CPU instead.')
    file.write("\n")
    device = torch.device("cpu")

file.flush()
#--------------------------------
#  Transformer parameters
#--------------------------------
# max_seq_length = 35
max_seq_length = 35
batch_size = 64
# batch_size = 64

#--------------------------------
#  GAN-BERT specific parameters
#--------------------------------
# number of hidden layers in the generator, 
# each of the size of the output space
num_hidden_layers_g = 1; 
# number of hidden layers in the discriminator, 
# each of the size of the input space
num_hidden_layers_d = 1; 
# size of the generator's input noisy vectors
noise_size = 100
# dropout to be applied to discriminator's input vectors
out_dropout_rate = 0.2

# Replicate labeled data to balance poorly represented datasets, 
# e.g., less than 1% of labeled material
apply_balance = False

#--------------------------------
#  Optimization parameters
#--------------------------------
learning_rate_discriminator = 5e-5
learning_rate_generator = 5e-5
epsilon = 1e-8
num_train_epochs = 25
multi_gpu = True
# Scheduler
apply_scheduler = False
warmup_proportion = 0.1
# Print
print_each_n_step = 50

#--------------------------------
#  Adopted Tranformer model
#--------------------------------
# Since this version is compatible with Huggingface transformers, you can uncomment
# (or add) transformer models compatible with GAN

# model_name = "bert-base-cased"
model_name = "UBC-NLP/MARBERT"
#model_name = "bert-base-uncased"
#model_name = "roberta-base"
#model_name = "albert-base-v2"
#model_name = "xlm-roberta-base"
#model_name = "amazon/bort"

#--------------------------------
#  Retrieve the TREC QC Dataset
#--------------------------------
# ! git clone https://github.com/crux82/ganbert

#  NOTE: in this setting 50 classes are involved

# !mkdir data


#### FULL DATA ####
# !mkdir data

# !gdown --id 1Jr6pnHMLklIr7jJdpxSJ-kIxsaJ79b_F #UNLABELED_NADI_TRAIN_TEST_DEV
# !gdown --id 1kY7qOXMSYJK-FbImAiTByov_ICFwB_BI #NADI_UNLABELED-10M-sampled
# !gdown --id 1z1Cb5JBFlUi8Fr6C5w_4z404kV6qZxY8 #TRAIN
# !gdown --id 1DPf3KGD29-RBV7TB2BoLP3y86kYJHQZU #TEST
# !gdown --id 1UJ3hu8DbO-JhgE_60tPs1unehONArE3M #TEST_NOT_CLEANED

# !mv qadi-train.tsv data
# !mv qadi-test.tsv data
# !mv unlabeled.tsv data
# !mv unlabeled-cleaned-sampled.tsv data
# !mv qadi-test-not-cleaned.tsv data

labeled_file = "./data/arSarcasm-train-gan.tsv"
# unlabeled_file = "./data/unlabeled.tsv"
unlabeled_file = "./data/nadi-unlabeled-50k-UNK.tsv"
test_filename = "./data/arSarcasm-test-gan.tsv"
test_filename_nc = "./data/arSarcasm-test-gan.tsv"


### Sampled Data ####
# !mkdir data

# !gdown --id 1_53-t9kelfSSE1ZpPBvN6HxrjOw1P82z
# !gdown --id 1ta_33A0AHCf7E15xU193C1znDcY0jmef
# !gdown --id 1QWOeH7u5rRxQeGK2nAA9rqzLqFbEcB8_

# !mv qadi-train-sampled.tsv data
# !mv qadi-test-sampled.tsv data
# !mv unlabeled-sampled.tsv data

# labeled_file = "./data/qadi-train-sampled.tsv"
# unlabeled_file = "./data/unlabeled-sampled.tsv"
# test_filename = "./data/qadi-test-sampled.tsv"

label_list = ['UNK_UNK','msa','egypt','levant','gulf','magreb']

# ! git clone https://github.com/crux82/ganbert

#  NOTE: in this setting 50 classes are involved
# labeled_file = "./ganbert/data/labeled.tsv"
# unlabeled_file = "./ganbert/data/unlabeled.tsv"
# test_filename = "./ganbert/data/test.tsv"

# label_list = ["UNK_UNK","ABBR_abb", "ABBR_exp", "DESC_def", "DESC_desc", 
#               "DESC_manner", "DESC_reason", "ENTY_animal", "ENTY_body", 
#               "ENTY_color", "ENTY_cremat", "ENTY_currency", "ENTY_dismed", 
#               "ENTY_event", "ENTY_food", "ENTY_instru", "ENTY_lang", 
#               "ENTY_letter", "ENTY_other", "ENTY_plant", "ENTY_product", 
#               "ENTY_religion", "ENTY_sport", "ENTY_substance", "ENTY_symbol", 
#               "ENTY_techmeth", "ENTY_termeq", "ENTY_veh", "ENTY_word", "HUM_desc", 
#               "HUM_gr", "HUM_ind", "HUM_title", "LOC_city", "LOC_country", 
#               "LOC_mount", "LOC_other", "LOC_state", "NUM_code", "NUM_count", 
#               "NUM_date", "NUM_dist", "NUM_money", "NUM_ord", "NUM_other", 
#               "NUM_perc", "NUM_period", "NUM_speed", "NUM_temp", "NUM_volsize", 
#               "NUM_weight"]

# """Load the Tranformer Model"""

transformer = AutoModel.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# """Function required to load the dataset"""

def get_qc_examples(input_file):
  # """Creates examples for the training and dev sets."""
  examples = []

  with open(input_file, 'r') as f:
      contents = f.read()
      file_as_list = contents.splitlines()
      for line in file_as_list[1:]:
          # split = line.split(" ")
          # question = ' '.join(split[1:])

          # text_a = question
          # inn_split = split[0].split(":")
          # label = inn_split[0] + "_" + inn_split[1]

          split = line.split("\t")
          question = split[1]

          text_a = question
          label = split[0]
          examples.append((text_a, label))
      f.close()

  return examples

# """**Load** the input QC dataset (fine-grained)"""

#Load the examples
labeled_examples = get_qc_examples(labeled_file)
unlabeled_examples = get_qc_examples(unlabeled_file)
test_examples = get_qc_examples(test_filename)
test_nc_examples = get_qc_examples(test_filename_nc)

# """Functions required to convert examples into Dataloader"""

def generate_data_loader(input_examples, label_masks, label_map, do_shuffle = False, balance_label_examples = False):
  # '''
  # Generate a Dataloader given the input examples, eventually masked if they are 
  # to be considered NOT labeled.
  # '''
  examples = []

  # Count the percentage of labeled examples  
  num_labeled_examples = 0
  for label_mask in label_masks:
    if label_mask: 
      num_labeled_examples += 1
  label_mask_rate = num_labeled_examples/len(input_examples)

  # if required it applies the balance
  for index, ex in enumerate(input_examples): 
    if label_mask_rate == 1 or not balance_label_examples:
      examples.append((ex, label_masks[index]))
    else:
      # IT SIMULATE A LABELED EXAMPLE
      if label_masks[index]:
        balance = int(1/label_mask_rate)
        balance = int(math.log(balance,2))
        if balance < 1:
          balance = 1
        for b in range(0, int(balance)):
          examples.append((ex, label_masks[index]))
      else:
        examples.append((ex, label_masks[index]))
  
  #-----------------------------------------------
  # Generate input examples to the Transformer
  #-----------------------------------------------
  input_ids = []
  input_mask_array = []
  label_mask_array = []
  label_id_array = []

  # Tokenization 
  for (text, label_mask) in examples:
    encoded_sent = tokenizer.encode(text[0], add_special_tokens=True, max_length=max_seq_length, padding="max_length", truncation=True)
    input_ids.append(encoded_sent)
    label_id_array.append(label_map[text[1]])
    label_mask_array.append(label_mask)
  
  # Attention to token (to ignore padded input wordpieces)
  for sent in input_ids:
    att_mask = [int(token_id > 0) for token_id in sent]                          
    input_mask_array.append(att_mask)
  # Convertion to Tensor
  input_ids = torch.tensor(input_ids) 
  input_mask_array = torch.tensor(input_mask_array)
  label_id_array = torch.tensor(label_id_array, dtype=torch.long)
  label_mask_array = torch.tensor(label_mask_array)

  # Building the TensorDataset
  dataset = TensorDataset(input_ids, input_mask_array, label_id_array, label_mask_array)

  if do_shuffle:
    sampler = RandomSampler
  else:
    sampler = SequentialSampler

  # Building the DataLoader
  return DataLoader(
              dataset,  # The training samples.
              sampler = sampler(dataset), 
              batch_size = batch_size) # Trains with this batch size.

def format_time(elapsed):
    # '''
    # Takes a time in seconds and returns a string hh:mm:ss
    # '''
    # Round to the nearest second.
    elapsed_rounded = int(round((elapsed)))
    # Format as hh:mm:ss
    return str(datetime.timedelta(seconds=elapsed_rounded))

# """Convert the input examples into DataLoader"""

label_map = {}
for (i, label) in enumerate(label_list):
  label_map[label] = i
#------------------------------
#   Load the train dataset
#------------------------------
train_examples = labeled_examples
#The labeled (train) dataset is assigned with a mask set to True
train_label_masks = np.ones(len(labeled_examples), dtype=bool)
#If unlabel examples are available
if unlabeled_examples:
  train_examples = train_examples + unlabeled_examples
  #The unlabeled (train) dataset is assigned with a mask set to False
  tmp_masks = np.zeros(len(unlabeled_examples), dtype=bool)
  train_label_masks = np.concatenate([train_label_masks,tmp_masks])

train_dataloader = generate_data_loader(train_examples, train_label_masks, label_map, do_shuffle = True, balance_label_examples = apply_balance)

#------------------------------
#   Load the test dataset
#------------------------------
#The labeled (test) dataset is assigned with a mask set to True
test_label_masks = np.ones(len(test_examples), dtype=bool)

test_dataloader = generate_data_loader(test_examples, test_label_masks, label_map, do_shuffle = False, balance_label_examples = False)

##NC
test_nc_label_masks = np.ones(len(test_examples), dtype=bool)
test_nc_dataloader = generate_data_loader(test_nc_examples, test_nc_label_masks, label_map, do_shuffle = False, balance_label_examples = False)

# """We define the Generator and Discriminator as discussed in https://www.aclweb.org/anthology/2020.acl-main.191/"""

#------------------------------
#   The Generator as in 
#   https://www.aclweb.org/anthology/2020.acl-main.191/
#   https://github.com/crux82/ganbert
#------------------------------
class Generator(nn.Module):
    def __init__(self, noise_size=100, output_size=512, hidden_sizes=[512], dropout_rate=0.1):
        super(Generator, self).__init__()
        layers = []
        hidden_sizes = [noise_size] + hidden_sizes
        for i in range(len(hidden_sizes)-1):
            layers.extend([nn.Linear(hidden_sizes[i], hidden_sizes[i+1]), nn.LeakyReLU(0.2, inplace=True), nn.Dropout(dropout_rate)])

        layers.append(nn.Linear(hidden_sizes[-1],output_size))
        self.layers = nn.Sequential(*layers)

    def forward(self, noise):
        output_rep = self.layers(noise)
        return output_rep

#------------------------------
#   The Discriminator
#   https://www.aclweb.org/anthology/2020.acl-main.191/
#   https://github.com/crux82/ganbert
#------------------------------
class Discriminator(nn.Module):
    def __init__(self, input_size=512, hidden_sizes=[512], num_labels=2, dropout_rate=0.1):
        super(Discriminator, self).__init__()
        self.input_dropout = nn.Dropout(p=dropout_rate)
        layers = []
        hidden_sizes = [input_size] + hidden_sizes
        for i in range(len(hidden_sizes)-1):
            layers.extend([nn.Linear(hidden_sizes[i], hidden_sizes[i+1]), nn.LeakyReLU(0.2, inplace=True), nn.Dropout(dropout_rate)])

        self.layers = nn.Sequential(*layers) #per il flatten
        self.logit = nn.Linear(hidden_sizes[-1],num_labels+1) # +1 for the probability of this sample being fake/real.
        self.softmax = nn.Softmax(dim=-1)

    def forward(self, input_rep):
        input_rep = self.input_dropout(input_rep)
        last_rep = self.layers(input_rep)
        logits = self.logit(last_rep)
        probs = self.softmax(logits)
        return last_rep, logits, probs

# """We instantiate the Discriminator and Generator"""

# The config file is required to get the dimension of the vector produced by 
# the underlying transformer
config = AutoConfig.from_pretrained(model_name)
hidden_size = int(config.hidden_size)
# Define the number and width of hidden layers
hidden_levels_g = [hidden_size for i in range(0, num_hidden_layers_g)]
hidden_levels_d = [hidden_size for i in range(0, num_hidden_layers_d)]

#-------------------------------------------------
#   Instantiate the Generator and Discriminator
#-------------------------------------------------
generator = Generator(noise_size=noise_size, output_size=hidden_size, hidden_sizes=hidden_levels_g, dropout_rate=out_dropout_rate)
discriminator = Discriminator(input_size=hidden_size, hidden_sizes=hidden_levels_d, num_labels=len(label_list), dropout_rate=out_dropout_rate)

# Put everything in the GPU if available
if torch.cuda.is_available():    
  generator.cuda()
  discriminator.cuda()
  transformer.cuda()
  if multi_gpu:
    transformer = torch.nn.DataParallel(transformer)

# file.write(config)

# """Let's go with the training procedure"""

# batch[0].shape[0]



from sklearn.metrics import f1_score

training_stats = []

# Measure the total training time for the whole run.
total_t0 = time.time()

#models parameters
transformer_vars = [i for i in transformer.parameters()]
d_vars = transformer_vars + [v for v in discriminator.parameters()]
g_vars = [v for v in generator.parameters()]

#optimizer
dis_optimizer = torch.optim.AdamW(d_vars, lr=learning_rate_discriminator)
gen_optimizer = torch.optim.AdamW(g_vars, lr=learning_rate_generator) 

#scheduler
if apply_scheduler:
  num_train_examples = len(train_examples)
  num_train_steps = int(num_train_examples / batch_size * num_train_epochs)
  num_warmup_steps = int(num_train_steps * warmup_proportion)

  scheduler_d = get_constant_schedule_with_warmup(dis_optimizer, 
                                           num_warmup_steps = num_warmup_steps)
  scheduler_g = get_constant_schedule_with_warmup(gen_optimizer, 
                                           num_warmup_steps = num_warmup_steps)

# For each epoch...
for epoch_i in range(0, num_train_epochs):
    # ========================================
    #               Training
    # ========================================
    # Perform one full pass over the training set.
    file.write("")
    file.write("\n")
    file.write('======== Epoch {:} / {:} ========'.format(epoch_i + 1, num_train_epochs))
    file.write("\n")
    file.write('Training...')
    file.write("\n")
    file.flush()

    # Measure how long the training epoch takes.
    t0 = time.time()

    # Reset the total loss for this epoch.
    tr_g_loss = 0
    tr_d_loss = 0

    # Put the model into training mode.
    transformer.train() 
    generator.train()
    discriminator.train()

    # For each batch of training data...
    for step, batch in enumerate(train_dataloader):

        # Progress update every print_each_n_step batches.
        if step % print_each_n_step == 0 and not step == 0:
            # Calculate elapsed time in minutes.
            elapsed = format_time(time.time() - t0)
            
            # Report progress.
            file.write('  Batch {:>5,}  of  {:>5,}.    Elapsed: {:}.'.format(step, len(train_dataloader), elapsed))
            file.write("\n")
            file.flush()

        # Unpack this training batch from our dataloader. 
        b_input_ids = batch[0].to(device)
        b_input_mask = batch[1].to(device)
        b_labels = batch[2].to(device)
        b_label_mask = batch[3].to(device)

        real_batch_size = b_input_ids.shape[0]
     
        # Encode real data in the Transformer
        model_outputs = transformer(b_input_ids, attention_mask=b_input_mask)
        hidden_states = model_outputs[-1]
        
        # Generate fake data that should have the same distribution of the ones
        # encoded by the transformer. 
        # First noisy input are used in input to the Generator
        noise = torch.zeros(real_batch_size, noise_size, device=device).uniform_(0, 1)
        # Gnerate Fake data
        gen_rep = generator(noise)

        # Generate the output of the Discriminator for real and fake data.
        # First, we put together the output of the tranformer and the generator
        disciminator_input = torch.cat([hidden_states, gen_rep], dim=0)
        # Then, we select the output of the disciminator
        features, logits, probs = discriminator(disciminator_input)

        # Finally, we separate the discriminator's output for the real and fake
        # data
        features_list = torch.split(features, real_batch_size)
        D_real_features = features_list[0]
        D_fake_features = features_list[1]
      
        logits_list = torch.split(logits, real_batch_size)
        D_real_logits = logits_list[0]
        D_fake_logits = logits_list[1]
        
        probs_list = torch.split(probs, real_batch_size)
        D_real_probs = probs_list[0]
        D_fake_probs = probs_list[1]

        #---------------------------------
        #  LOSS evaluation
        #---------------------------------
        # Generator's LOSS estimation
        g_loss_d = -1 * torch.mean(torch.log(1 - D_fake_probs[:,-1] + epsilon))
        g_feat_reg = torch.mean(torch.pow(torch.mean(D_real_features, dim=0) - torch.mean(D_fake_features, dim=0), 2))
        g_loss = g_loss_d + g_feat_reg
  
        # Disciminator's LOSS estimation
        logits = D_real_logits[:,0:-1]
        log_probs = F.log_softmax(logits, dim=-1)
        # The discriminator provides an output for labeled and unlabeled real data
        # so the loss evaluated for unlabeled data is ignored (masked)
        label2one_hot = torch.nn.functional.one_hot(b_labels, len(label_list))
        per_example_loss = -torch.sum(label2one_hot * log_probs, dim=-1)
        per_example_loss = torch.masked_select(per_example_loss, b_label_mask.to(device))
        labeled_example_count = per_example_loss.type(torch.float32).numel()

        # It may be the case that a batch does not contain labeled examples, 
        # so the "supervised loss" in this case is not evaluated
        if labeled_example_count == 0:
          D_L_Supervised = 0
        else:
          D_L_Supervised = torch.div(torch.sum(per_example_loss.to(device)), labeled_example_count)
                 
        D_L_unsupervised1U = -1 * torch.mean(torch.log(1 - D_real_probs[:, -1] + epsilon))
        D_L_unsupervised2U = -1 * torch.mean(torch.log(D_fake_probs[:, -1] + epsilon))
        d_loss = D_L_Supervised + D_L_unsupervised1U + D_L_unsupervised2U

        #---------------------------------
        #  OPTIMIZATION
        #---------------------------------
        # Avoid gradient accumulation
        gen_optimizer.zero_grad()
        dis_optimizer.zero_grad()

        # Calculate weigth updates
        # retain_graph=True is required since the underlying graph will be deleted after backward
        g_loss.backward(retain_graph=True)
        d_loss.backward() 
        
        # Apply modifications
        gen_optimizer.step()
        dis_optimizer.step()

        # A detail log of the individual losses
        #file.write("{0:.4f}\t{1:.4f}\t{2:.4f}\t{3:.4f}\t{4:.4f}".
        #      format(D_L_Supervised, D_L_unsupervised1U, D_L_unsupervised2U,
        #             g_loss_d, g_feat_reg))

        # Save the losses to print them later
        tr_g_loss += g_loss.item()
        tr_d_loss += d_loss.item()

        # Update the learning rate with the scheduler
        if apply_scheduler:
          scheduler_d.step()
          scheduler_g.step()

    # Calculate the average loss over all of the batches.
    avg_train_loss_g = tr_g_loss / len(train_dataloader)
    avg_train_loss_d = tr_d_loss / len(train_dataloader)             
    
    # Measure how long this epoch took.
    training_time = format_time(time.time() - t0)

    file.write("")
    file.write("\n")
    file.write("  Average training loss generetor: {0:.3f}".format(avg_train_loss_g))
    file.write("\n")
    file.write("  Average training loss discriminator: {0:.3f}".format(avg_train_loss_d))
    file.write("\n")
    file.write("  Training epcoh took: {:}".format(training_time))
    file.write("\n")
    file.flush()
    # ========================================
    #     TEST ON THE EVALUATION DATASET
    # ========================================
    # After the completion of each training epoch, measure our performance on
    # our test set.
    file.write("")
    file.write("Running Test...")
    file.write("\n")

    t0 = time.time()

    # Put the model in evaluation mode--the dropout layers behave differently
    # during evaluation.
    transformer.eval() #maybe redundant
    discriminator.eval()
    generator.eval()

    # Tracking variables 
    total_test_accuracy = 0
   
    total_test_loss = 0
    nb_test_steps = 0

    all_preds = []
    all_labels_ids = []

    #loss
    nll_loss = torch.nn.CrossEntropyLoss(ignore_index=-1)

    # Evaluate data for one epoch
    for batch in test_dataloader:
        
        # Unpack this training batch from our dataloader. 
        b_input_ids = batch[0].to(device)
        b_input_mask = batch[1].to(device)
        b_labels = batch[2].to(device)
        
        # Tell pytorch not to bother with constructing the compute graph during
        # the forward pass, since this is only needed for backprop (training).
        with torch.no_grad():        
            model_outputs = transformer(b_input_ids, attention_mask=b_input_mask)
            hidden_states = model_outputs[-1]
            _, logits, probs = discriminator(hidden_states)
            ###log_probs = F.log_softmax(probs[:,1:], dim=-1)
            filtered_logits = logits[:,0:-1]
            # Accumulate the test loss.
            total_test_loss += nll_loss(filtered_logits, b_labels)
            
        # Accumulate the predictions and the input labels
        _, preds = torch.max(filtered_logits, 1)
        all_preds += preds.detach().cpu()
        all_labels_ids += b_labels.detach().cpu()

    # Report the final accuracy for this validation run.
    all_preds = torch.stack(all_preds).numpy()
    all_labels_ids = torch.stack(all_labels_ids).numpy()
    test_accuracy = np.sum(all_preds == all_labels_ids) / len(all_preds)
    test_f1 = f1_score(all_labels_ids, all_preds, average="macro")
    file.write("  Test Accuracy: {0:.3f}".format(test_accuracy))
    file.write("\n")
    file.write("  Test F1: {0:.3f}".format(test_f1))
    file.write("\n")

    # Calculate the average loss over all of the batches.
    avg_test_loss = total_test_loss / len(test_dataloader)
    avg_test_loss = avg_test_loss.item()
    
    # Measure how long the validation run took.
    test_time = format_time(time.time() - t0)
    
    file.write("  Test Loss: {0:.3f}".format(avg_test_loss))
    file.write("\n")
    file.write("  Test took: {:}".format(test_time))
    file.write("\n")
    file.flush()

    confusion_matrix = np.zeros((6, 6), dtype=np.int16)
    for i in range (len(all_preds)):
      confusion_matrix[all_labels_ids[i], all_preds[i]] += 1
    file.write("Confusion Matrix after epoch completion: \n")
    file.write(str(confusion_matrix))
    file.write("\n")

    # Record all statistics from this epoch.
    training_stats.append(
        {
            'epoch': epoch_i + 1,
            'Training Loss generator': avg_train_loss_g,
            'Training Loss discriminator': avg_train_loss_d,
            'Valid. Loss': avg_test_loss,
            'Valid. Accur.': test_accuracy,
            'Test F1': test_f1,
            'Test. Accur.': test_accuracy,
            'Training Time': training_time,
            'Test Time': test_time
        }
    )


for stat in training_stats:
  file.write(str(stat))
  file.write("\n")

# confusion_matrix = np.zeros((19, 19), dtype=np.int16)
# for i in range (len(all_preds)):
#     confusion_matrix[all_labels_ids[i], all_preds[i]] += 1

# file.write(str(confusion_matrix))
# file.write("\n")

file.write("\nTraining complete!")
file.write("\n")

file.write("Total training took {:} (h:mm:ss)".format(format_time(time.time()-total_t0)))
file.write("\n")


file.write(" Evaluating Original Test Data Without Cleaning")
file.write("\n")
file.flush()

# ==============ADDED CELL ==== NOT CLEANED TEST SET ==========================
    #     TEST ON THE  UN-CLEANED EVALUATION DATASET
    # ========================================
    # ORIGINAL TEST SET NOT CLEANED.
file.write("")
file.write("\n")
file.write("Running Test...")
file.write("\n")

t0 = time.time()

# Put the model in evaluation mode--the dropout layers behave differently
# during evaluation.
transformer.eval() #maybe redundant
discriminator.eval()
generator.eval()

# Tracking variables 
total_test_accuracy = 0

total_test_loss = 0
nb_test_steps = 0

all_preds = []
all_labels_ids = []

#loss
nll_loss = torch.nn.CrossEntropyLoss(ignore_index=-1)

# Evaluate data for one epoch
for batch in test_nc_dataloader:
    
    # Unpack this training batch from our dataloader. 
    b_input_ids = batch[0].to(device)
    b_input_mask = batch[1].to(device)
    b_labels = batch[2].to(device)
    
    # Tell pytorch not to bother with constructing the compute graph during
    # the forward pass, since this is only needed for backprop (training).
    with torch.no_grad():        
        model_outputs = transformer(b_input_ids, attention_mask=b_input_mask)
        hidden_states = model_outputs[-1]
        _, logits, probs = discriminator(hidden_states)
        ###log_probs = F.log_softmax(probs[:,1:], dim=-1)
        filtered_logits = logits[:,0:-1]
        # Accumulate the test loss.
        total_test_loss += nll_loss(filtered_logits, b_labels)
        
    # Accumulate the predictions and the input labels
    _, preds = torch.max(filtered_logits, 1)
    all_preds += preds.detach().cpu()
    all_labels_ids += b_labels.detach().cpu()

# Report the final accuracy for this validation run.
all_preds = torch.stack(all_preds).numpy()
all_labels_ids = torch.stack(all_labels_ids).numpy()
test_accuracy = np.sum(all_preds == all_labels_ids) / len(all_preds)
test_f1 = f1_score(all_labels_ids, all_preds, average="macro")
file.write(" Original Test not cleaned - Accuracy: {0:.3f}".format(test_accuracy))
file.write("\n")
file.write(" Original Test not cleaned - F1: {0:.3f}".format(test_f1))
file.write("\n")

# Calculate the average loss over all of the batches.
avg_test_loss = total_test_loss / len(test_dataloader)
avg_test_loss = avg_test_loss.item()

# Measure how long the validation run took.
test_time = format_time(time.time() - t0)

file.write(" Original Test not cleaned - Loss: {0:.3f}".format(avg_test_loss))
file.write("\n")
file.write(" Original Test not cleaned - Loss took: {:}".format(test_time))
file.write("\n")

# file.write(all_preds)
# file.write("\n")
# file.write(all_labels_ids)
# file.write("\n")
# label_list[all_preds[0]]

confusion_matrix = np.zeros((6, 6), dtype=np.int16)
for i in range (len(all_preds)):
    confusion_matrix[all_labels_ids[i], all_preds[i]] += 1
file.write("Confusion matrix of original test data (no cleaning): \n")
file.write(str(confusion_matrix))
file.write("\n")
file.flush()
file.close()