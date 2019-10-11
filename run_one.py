import argparse
import json
import multiprocessing
import os
import shutil
import subprocess
from buffet import Buffet, draw_frame


def generate_video(frames_dir, output):
    args = ['ffmpeg', '-y', '-r', '10', '-f', 'image2', '-i', frames_dir + '/%06d.png',
            '-vcodec', 'libx264', '-crf', '25', '-pix_fmt', 'yuv420p',
            '-vf', 'pad=width=ceil(iw/2)*2:height=ceil(ih/2)*2', output]
    subprocess.run(args)

    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rate', type=float, default=1.0)
    parser.add_argument('--method', choices=['classic', 'vline', 'rogue', 'skippable'], required=True)
    parser.add_argument('--output', default='buffet.json')
    parser.add_argument('--draw-video')
    parser.add_argument('--simple-video', action='store_true')  # draw less, for gif
    parser.add_argument('--steps', default=1500, type=int)
    parser.add_argument('--draw-video-every', default=100, type=int)
    # todo: add more arguments
    args = parser.parse_args()

    if args.draw_video:
        frames_dir = args.draw_video + '.frames'
        if os.path.exists(frames_dir):
            shutil.rmtree(frames_dir)
        os.makedirs(frames_dir)

    b = Buffet(rate=args.rate, method=args.method)
    pool = multiprocessing.Pool(10)  # only used for drawing, see comment in draw_frame
    for step in range(args.steps):
        print('###### step', step)
        data = b.step()
        with open(args.output, 'w') as f:
            json.dump(data, f)
        if args.draw_video:
            pool.apply(draw_frame, (b, '%s/%06d.png' % (frames_dir, step), args.simple_video))
            if step % args.draw_video_every == args.draw_video_every-1:
                pool.apply(generate_video, (frames_dir, args.draw_video))
