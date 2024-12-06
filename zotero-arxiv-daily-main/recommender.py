import numpy as np
from sentence_transformers import SentenceTransformer
import arxiv
from datetime import datetime

def rerank_paper(candidate: list[arxiv.Result], corpus: list[dict], model: str = 'avsolatorio/GIST-small-Embedding-v0') -> list[arxiv.Result]:
    encoder = SentenceTransformer(model)
    
    # 按照日期对 corpus 进行排序，从最新到最旧
    corpus = sorted(corpus, key=lambda x: datetime.strptime(x['data']['dateAdded'], '%Y-%m-%dT%H:%M:%SZ'), reverse=True)
    # 增加时间衰减权重
    time_decay_weight = 1 / (1 + np.log10(np.arange(len(corpus)) + 1))
    time_decay_weight = time_decay_weight / time_decay_weight.sum()
    
    # 获取 corpus 和候选论文的特征表示
    corpus_feature = encoder.encode([paper['data']['abstractNote'] for paper in corpus])
    candidate_feature = encoder.encode([paper.summary for paper in candidate])

    # 计算相似度
    sim = np.dot(candidate_feature, corpus_feature.T)  # [n_candidate, n_corpus], 使用点积计算相似度
    scores = (sim * time_decay_weight).sum(axis=1) * 10  # [n_candidate]

    # 为候选论文添加分数并排序
    for s, c in zip(scores, candidate):
        c.score = s.item()
    candidate = sorted(candidate, key=lambda x: x.score, reverse=True)
    
    return candidate
