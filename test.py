import os.path
import logging
import torch
import argparse
import json
import glob

from pprint import pprint
from utils.model_summary import get_model_flops
from utils import utils_logger
from utils import utils_image as util


def select_model(args, device):
    # Model ID is assigned according to the order of the submissions.
    # Different networks are trained with input range of either [0,1] or [0,255]. The range is determined manually.
    model_id = args.model_id
    if model_id == 0:
        # CodeFormer baseline, NIPS 2022
        from models.team00_CodeFormer import main as CodeFormer
        name = f"{model_id:02}_CodeFormer_baseline"
        model_path = os.path.join('model_zoo', 'team00_CodeFormer')
        model_func = CodeFormer
    elif model_id==2:
        name = f"{model_id:02}_faceRes"
        from models.team02_faceRes.combined_inference import run_inference
        #绝对路径看情况进行修改
        model_path=os.path.join("model_zoo", 'team02_faceRes')

        model_func=run_inference
    elif model_id==200:
        name = f"{model_id:02}_ZSSR"
        from models.team02_ZSSR.zssr import ZSSRWrapper
        from models.team02_ZSSR.config import set_config
        config = set_config()
        config.accelerator = "gpu" if device.type == "cuda" else "cpu"
        zssr_wrapper = ZSSRWrapper(config)
        model_path = None
        model_func = zssr_wrapper.wrapper

        # from models.team01_ZSSR.zssr import ZSSRWrapper
        # from models.team01_ZSSR.config import set_config
        # config = set_config()
        # config.accelerator = "gpu" if device.type == "cuda" else "cpu"
        # zssr_wrapper = ZSSRWrapper(config)
        # model_path = None
        # model_func = zssr_wrapper.wrapper

    return model_func, model_path, name


def run(model_func, model_name, model_path, device, args, mode="test"):
    # --------------------------------
    # dataset path
    # --------------------------------
    if mode == "valid":
        data_path = args.valid_dir
    elif mode == "test":
        data_path = args.test_dir
    assert data_path is not None, "Please specify the dataset path for validation or test."
    
    save_path = os.path.join(args.save_dir, model_name, mode)
    util.mkdir(save_path)

    data_paths = []
    save_paths = []
    for dataset_name in ("CelebA", "Wider-Test", "LFW-Test", "WebPhoto-Test", "CelebChild-Test"):
        data_paths.append(os.path.join(data_path, dataset_name))
        save_paths.append(os.path.join(save_path, dataset_name))
        util.mkdir(save_paths[-1])

    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)

    start.record()
    for data_path, save_path in zip(data_paths, save_paths):
        print(model_path)
        model_func(model_dir=model_path, input_path=data_path, output_path=save_path, device=device)
    end.record()
    torch.cuda.synchronize()
    print(f"Model {model_name} runtime (Including I/O): {start.elapsed_time(end)} ms")


def main(args):

    utils_logger.logger_info("NTIRE2025-RealWorld-Face-Restoration", log_path="NTIRE2025-RealWorld-Face-Restoration.log")
    logger = logging.getLogger("NTIRE2025-RealWorld-Face-Restoration")

    # --------------------------------
    # basic settings
    # --------------------------------
    torch.cuda.current_device()
    torch.cuda.empty_cache()
    torch.backends.cudnn.benchmark = False
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    json_dir = os.path.join(os.getcwd(), "results.json")
    if not os.path.exists(json_dir):
        results = dict()
    else:
        with open(json_dir, "r") as f:
            results = json.load(f)

    # --------------------------------
    # load model
    # --------------------------------
    model_func, model_path, model_name = select_model(args, device)
    logger.info(model_name)

    # if model not in results:
    if args.valid_dir is not None:
        run(model_func, model_name, model_path, device, args, mode="valid")
        
    if args.test_dir is not None:
        run(model_func, model_name, model_path, device, args, mode="test")

if __name__ == "__main__":
    parser = argparse.ArgumentParser("NTIRE2025-RealWorld-Face-Restoration")
    parser.add_argument("--valid_dir", default=None, type=str, help="Path to the validation set")
    parser.add_argument("--test_dir", default=None, type=str, help="Path to the test set")
    parser.add_argument("--save_dir", default="NTIRE2025-RealWorld-Face-Restoration/results", type=str)
    parser.add_argument("--model_id", default=0, type=int)

    args = parser.parse_args()
    pprint(args)

    main(args)
