from tempfile import TemporaryDirectory
import arxiv
import tarfile
import re
from llama_cpp import Llama

def get_paper_summary(paper: arxiv.Result) -> str:
    with TemporaryDirectory() as tmpdirname:
        file = paper.download_source(dirpath=tmpdirname)
        with tarfile.open(file) as tar:
            tex_files = [f for f in tar.getnames() if f.endswith('.tex')]
            if len(tex_files) == 0:
                return None, None  # 返回None以处理空情况
            # 读取所有的tex文件
            introduction = ""
            conclusion = ""
            for t in tex_files:
                f = tar.extractfile(t)
                content = f.read().decode('utf-8')
                # 去除注释
                content = re.sub(r'%.*\n', '\n', content)
                content = re.sub(r'\\begin{comment}.*?\\end{comment}', '', content, flags=re.DOTALL)
                content = re.sub(r'\\iffalse.*?\\fi', '', content, flags=re.DOTALL)
                # 去除冗余的换行
                content = re.sub(r'\n+', '\n', content)
                # 去除引用
                content = re.sub(r'~?\\cite.?\{.*?\}', '', content)
                # 去除图和表
                content = re.sub(r'\\begin\{figure\}.*?\\end\{figure\}', '', content, flags=re.DOTALL)
                content = re.sub(r'\\begin\{table\}.*?\\end\{table\}', '', content, flags=re.DOTALL)
                
                # 寻找引言和结论
                match = re.search(r'\\section\{Introduction\}.*?(\\section|\\end\{document\}|\\bibliography|\\appendix|$)', content, flags=re.DOTALL)
                if match:
                    introduction = match.group(0)
                match = re.search(r'\\section\{Conclusion\}.*?(\\section|\\end\{document\}|\\bibliography|\\appendix|$)', content, flags=re.DOTALL)
                if match:
                    conclusion = match.group(0)
                
    return introduction, conclusion

def get_biorxiv_paper_summary(paper: dict) -> str:
    """
    从 bioRxiv 论文中提取引言和结论
    :param paper: bioRxiv 论文信息字典
    :return: 引言和结论
    """
    introduction = ""
    conclusion = ""
    
    # 假设 bioRxiv 论文信息中包含 'abstract' 和 'content'
    # 这里可以进行调整以适应真实的 bioRxiv 格式
    if 'abstract' in paper:
        introduction = paper['abstract']
    
    if 'content' in paper:
        content = paper['content']
        match = re.search(r'\\section\{Conclusion\}.*?(\\section|\\end\{document\}|\\bibliography|\\appendix|$)', content, flags=re.DOTALL)
        if match:
            conclusion = match.group(0)
    
    return introduction, conclusion

def get_paper_tldr(paper: arxiv.Result, model: Llama) -> str:
    try:
        introduction, conclusion = get_paper_summary(paper)
    except Exception as e:
        introduction, conclusion = "", ""
        print(f"Error processing paper: {e}")
    
    prompt = """Given the title, abstract, introduction and the conclusion (if any) of a paper in latex format, generate a one-sentence TLDR summary:
    
    \\title{__TITLE__}
    \\begin{abstract}__ABSTRACT__\\end{abstract}
    __INTRODUCTION__
    __CONCLUSION__
    """
    prompt = prompt.replace('__TITLE__', paper.title)
    prompt = prompt.replace('__ABSTRACT__', paper.summary)
    prompt = prompt.replace('__INTRODUCTION__', introduction)
    prompt = prompt.replace('__CONCLUSION__', conclusion)
    
    prompt_tokens = model.tokenize(prompt.encode('utf-8'))
    prompt_tokens = prompt_tokens[:3800]  # 截断到 3800 tokens
    prompt = model.detokenize(prompt_tokens).decode('utf-8')
    
    response = model.create_chat_completion(
        messages=[
            {"role": "system", "content": "You are an assistant who perfectly summarizes scientific paper, and gives the core idea of the paper to the user."},
            {
                "role": "user",
                "content": prompt
            }
        ],
        top_k=0,
        temperature=0
    )
    return response['choices'][0]['message']['content']
