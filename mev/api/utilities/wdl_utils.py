import re
import os
import glob

WDL_SUFFIX = '.wdl'

def get_docker_images_in_repo(operation_dir):
    '''
    Given a directory containing WDL files, 
    look through those files and grab all the docker container
    declarations.

    Return a list 
    '''
    wdl_files = glob.glob(os.path.join(operation_dir, '*' + WDL_SUFFIX))
    image_set = set()
    for wdl in wdl_files:
        wdl_text = open(wdl, 'r').read()
        intermediate_image_set = extract_docker_runtimes(wdl_text)
        image_set = image_set.union(intermediate_image_set)
    return list(image_set)

def parse_docker_runtime_declaration(docker_str):
    '''
    This function parses the docker string that is parsed out of 
    the WDL file.  Returns a tuple of strings giving the image name and tag,
    e.g. ('docker.io/user/img', 'v1.0') 
    '''
    # now if we split on ':', we get something like: (note the quotes)
    # ['docker', ' "docker.io/foo/bar', 'tag"']
    # if a tag is not specified, this list will have length 2.  We enforce that images are tagged, so raise excpetion
    contents = [x.strip() for x in docker_str.split(':')] # now looks like ['docker', '"docker.io/foo/bar', 'tag"']
    if len(contents) == 3:
        image_name = contents[1][1:] # strip off the leading double-quote, leaving 'docker.io/foo/bar'
        tag = contents[-1][:-1] # strip off the trailing double-quote, leaving 'tag'
    elif len(contents) == 2:
        image_name = contents[1][1:-1] # strip off the leading AND trailing double-quote, leaving 'docker.io/foo/bar'
        tag = None
    return (image_name, tag)

def extract_docker_runtimes(wdl_text):
    '''
    Parses the text from a WDL file and returns a set of Docker image "handles"
    '''
    # For parsing the WDL files:
    task_pattern = 'task\s+\w+\s?\{' # only finds the task definition line- does not extract the entire block of the task
    runtime_pattern = 'runtime\s?\{.*?\}' # extracts the entire runtime section, including the braces
    docker_pattern = 'docker\s?:\s?".*?"' # extracts the docker specification, e.g. docker: `"repo/user/image:tag"`

    # prepare a list to return:
    docker_runtimes = []

    # get the total number of tasks in this WDL file:
    task_match = re.findall(task_pattern, wdl_text, re.DOTALL)
    num_tasks = len(task_match)

    # we now know there are num_tasks tasks defined in the WDL file.  Therefore, there should be num_tasks runtime sections
    # Find all of those and parse each:
    runtime_sections = re.findall(runtime_pattern, wdl_text, re.DOTALL)
    if len(runtime_sections) != num_tasks:
        raise Exception('There were %d tasks defined, '
            'but only %d runtime sections found.  Check your WDL file.' % (num_tasks, len(runtime_sections)))
    elif num_tasks > 0: # tasks are defined and the number of runtime sections are consistent with tasks
        for runtime_section in runtime_sections:
            docker_match = re.search(docker_pattern, runtime_section, re.DOTALL)
            if docker_match:
                # the docker line was found.  Now parse it.
                docker_str = docker_match.group()  # something like 'docker: "docker.io/foo/bar:tag"'
                image_name, tag = parse_docker_runtime_declaration(docker_str)
                # "add" them back together, so we end up with 'docker.io/foo/bar:tag'
                if tag is not None:
                    docker_runtimes.append('%s:%s' % (image_name, tag))
                else:
                    docker_runtimes.append(image_name)
            else: # docker spec not found in this runtime.  That's a problem
                raise Exception('Could not parse a docker image specification from your '
                    'runtime section: %s.  Check file' % runtime_section)
    # if we make it here, no exceptions were raised.  Return the docker images found:
    return set(docker_runtimes)

def edit_runtime_containers(operation_dir, name_mapping):
    '''
    `operation_dir` is a folder where all the workflow files reside
    `name_mapping` is a dict that maps the original container runtimes
    to the new names (which have the proper tagging)
    '''
    wdl_files = glob.glob(os.path.join(operation_dir, '*' + WDL_SUFFIX))
    for wdl in wdl_files:
        wdl_text = open(wdl, 'r').read()
        for orig_image_str, new_image_str in name_mapping.items():
            wdl_text = re.sub(orig_image_str, new_image_str, wdl_text)
        with open(wdl, 'w') as fout:
            fout.write(wdl_text)