''' Define the Layers '''
import torch.nn as nn
import torch
from transformer.SubLayers import MultiHeadAttention, PositionwiseFeedForward


class EncoderLayer(nn.Module):
    ''' Compose with two layers '''

    def __init__(self, d_model, d_inner, n_head, d_k, d_v, dropout=0.1):
        super(EncoderLayer, self).__init__()
        self.slf_attn = MultiHeadAttention(n_head, d_model, d_k, d_v, dropout=dropout)
        self.pos_ffn = PositionwiseFeedForward(d_model, d_inner, dropout=dropout)

    def forward(self, enc_input, slf_attn_mask=None):
        enc_output, enc_slf_attn = self.slf_attn(
            enc_input, enc_input, enc_input, mask=slf_attn_mask)                    # 3个相同的input做输入 (256, 36, 512), 输出enc_output[256,8,512]和enc_slf_attn[256,8,36,36]
        enc_output = self.pos_ffn(enc_output)                                       # 由于这里是position-wise，即长度为36的序列中每个词的注意力做ffn，因此输入的矩阵形式一定是bach×seq_len×(d_k*n_head),ffn是对最后一个维度d_k*n_head做前馈

        return enc_output, enc_slf_attn                                             # enc_output [256, 36, 512], 长度为36的序列，每个word对应的8个头的注意力加权输出


class DecoderLayer(nn.Module):
    ''' Compose with three layers '''

    def __init__(self, d_model, d_inner, n_head, d_k, d_v, dropout=0.1):
        super(DecoderLayer, self).__init__()
        self.slf_attn = MultiHeadAttention(n_head, d_model, d_k, d_v, dropout=dropout)
        self.enc_attn = MultiHeadAttention(n_head, d_model, d_k, d_v, dropout=dropout)
        self.pos_ffn = PositionwiseFeedForward(d_model, d_inner, dropout=dropout)

    def forward(
            self, dec_input, enc_output,
            slf_attn_mask=None, dec_enc_attn_mask=None):
        dec_output, dec_slf_attn = self.slf_attn(                                   # 自注意力，dec_output[256, 32, 512], dec_slf_attn[256,8,32,32]
            dec_input, dec_input, dec_input, mask=slf_attn_mask)
        dec_output, dec_enc_attn = self.enc_attn(                                   # cross注意力，decoder第一层的自注意力输出做为Q与encoder输出做为K，V
            dec_output, enc_output, enc_output, mask=dec_enc_attn_mask)
        dec_output = self.pos_ffn(dec_output)                                       # dec_output[256,32,512]
        return dec_output, dec_slf_attn, dec_enc_attn
