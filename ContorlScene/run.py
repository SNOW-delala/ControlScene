import os
import json
import subprocess
import time

def main():
    time1 = time.time()
    prompt_file = '/root/autodl-tmp/SceneDreamer360/data/prompt.txt'
    test_file_root = '/root/autodl-tmp/SceneDreamer360/data/Matterport3D/mp3d_skybox/e9zR4mvMWw7/blip3_stitched/'
    test_file_name = 'test.txt'
    config_file = '/root/autodl-tmp/SceneDreamer360/config.json'
    log_file = '/root/autodl-tmp/SceneDreamer360/logs/log.txt'
    conda_env = os.getenv('CONDA_DEFAULT_ENV')
    print(conda_env)

    # 读取prompt.txt文件中的内容
    with open(prompt_file, 'r', encoding='utf-8') as file:
        prompts = file.readlines()

    # 遍历每个prompt
    for i, prompt in enumerate(prompts):
        # 重命名测试文件
        new_test_file_name = f'{i+0}.txt'
        os.rename(test_file_root + test_file_name, test_file_root + new_test_file_name)
        test_file_name = new_test_file_name
        new_test_file_path = test_file_root + new_test_file_name

        # 将当前prompt写入重命名后的文件
        with open(new_test_file_path, 'w', encoding='utf-8') as file:
            file.write(prompt)

        # 读取config文件内容
        with open(config_file, 'r', encoding='utf-8') as file:
            config_data = json.load(file)

        # 修改config文件中的"text"字段
        config_data['text'] = new_test_file_path

        # 将修改后的内容写回config文件
        with open(config_file, 'w', encoding='utf-8') as file:
            json.dump(config_data, file, ensure_ascii=False, indent=4)

        # 执行main.py文件
        command = 'WANDB_MODE=offline WANDB_RUN_ID=4142dlo4 python main.py predict --data=Matterport3D --model=PanFusion --ckpt_path=last'
        result = subprocess.run(command, shell=True)

        # 写入日志文件
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f'Executed command for prompt {i+1}: {prompt.strip()}\n')
            log.write(f'Result: {result.returncode}\n\n')
    
    time2 = time.time()
    print("take time:",time2-time1)

if __name__ == "__main__":
    main()
