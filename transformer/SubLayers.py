''' Define the sublayers in encoder/decoder layer '''
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
from transformer.Modules import ScaledDotProductAttention

class MultiHeadAttention(nn.Module):
    ''' Multi-Head Attention module '''

    def __init__(self, n_head, d_model, d_k, d_v, dropout=0.1):
        super().__init__()

        self.n_head = n_head
        self.d_k = d_k
        self.d_v = d_v

        self.w_qs = nn.Linear(d_model, n_head * d_k, bias=False)            # in_features=512, out_features=512
        self.w_ks = nn.Linear(d_model, n_head * d_k, bias=False)            # in_features=512, out_features=512
        self.w_vs = nn.Linear(d_model, n_head * d_v, bias=False)            # in_features=512, out_features=512
        self.fc = nn.Linear(n_head * d_v, d_model, bias=False)

        self.attention = ScaledDotProductAttention(temperature=d_k ** 0.5)

        self.dropout = nn.Dropout(dropout)
        self.layer_norm = nn.LayerNorm(d_model, eps=1e-6)


    def forward(self, q, k, v, mask=None):

        d_k, d_v, n_head = self.d_k, self.d_v, self.n_head
        sz_b, len_q, len_k, len_v = q.size(0), q.size(1), k.size(1), v.size(1)  # 256, 36, 36, 36

        residual = q    # (256,36,512)

        # Pass through the pre-attention projection: b x lq x (n*dv)
        # Separate different heads: b x lq x n x dv
        q = self.w_qs(q).view(sz_b, len_q, n_head, d_k)             # 对输入做线型变换后得到Q矩阵：36个词，每个词有8个头,每个头有64维，转为多头的格式(256, 36, 8, 64)，注意这里没有直接展开成(256,8,36,64)是因为linear输出的是dk*n_head,需要通过转置实现
        k = self.w_ks(k).view(sz_b, len_k, n_head, d_k)             # K
        v = self.w_vs(v).view(sz_b, len_v, n_head, d_v)             # V

        # Transpose for attention dot product: b x n x lq x dv
        q, k, v = q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2)   # 这里转为共8个头，每个头有36*64, (256, 8, 36, 64)

        if mask is not None:
            mask = mask.unsqueeze(1)   # For head axis broadcasting.        # (256,1,36) → (256,1,1,36)，broadcast的规则是有一个轴等于1可以自动broadcast

        q, attn = self.attention(q, k, v, mask=mask)                        # q = [256, 8, 36, 64], attn=[256, 8, 36, 36]

        # Transpose to move the head dimension back: b x lq x n x dv
        # Combine the last two dimensions to concatenate all the heads together: b x lq x (n*dv)
        q = q.transpose(1, 2).contiguous().view(sz_b, len_q, -1)            # 转置[256, 36, 8, 64]后将最后两维转为n_head*dv [256,8,512]，以便送入linear
        q = self.dropout(self.fc(q))
        q += residual

        q = self.layer_norm(q)

        return q, attn


class PositionwiseFeedForward(nn.Module):
    ''' A two-feed-forward-layer module '''

    def __init__(self, d_in, d_hid, dropout=0.1):
        super().__init__()
        self.w_1 = nn.Linear(d_in, d_hid) # position-wise                   # position-wise是指36长度的序列每个位置的词做线型层，即8个头每个头64维的矢量共512维输入矩阵
        self.w_2 = nn.Linear(d_hid, d_in) # position-wise
        self.layer_norm = nn.LayerNorm(d_in, eps=1e-6)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):

        residual = x

        x = self.w_2(F.relu(self.w_1(x)))
        x = self.dropout(x)
        x += residual

        x = self.layer_norm(x)

        return x
