function phase3_matlab()
% Phase 3: trusted synthetic input with restricted mathematical AST.
% Never use eval/str2num or execute arbitrary input commands.
root = getenv('GITHUB_WORKSPACE');
if isempty(root), root = pwd; end
folder = fullfile(root, 'math_ir_io');
bundle = jsondecode(fileread(fullfile(folder, 'input.json')));
manifest = jsondecode(fileread(fullfile(folder, 'manifest.json')));
sage = jsondecode(fileread(fullfile(folder, 'sage_result.json')));
if ~strcmp(bundle.schema, 'math-ir/0.1') || ~strcmp(manifest.schema, 'math-ir-phase3/1')
    error('Math IR schema mismatch');
end
numCases = numel(bundle.cases);
if numCases ~= numel(sage.results) || numCases ~= numel(manifest.cases)
    error('Input count mismatch');
end
results = repmat(struct('case_id', '', 'input_sha256', '', ...
    'metadata_sha256', '', 'unit', '', 'upstream_result', struct(), ...
    'result', struct()), 1, numCases);
for i = 1:numCases
    item = bundle.cases(i);
    meta = manifest.cases(i);
    upstream = sage.results(i);
    if ~strcmp(item.case_id, meta.case_id) || ~strcmp(item.case_id, upstream.case_id)
        error('Case ID mismatch');
    end
    if ~strcmp(meta.input_sha256, upstream.input_sha256)
        error('Sage input hash mismatch');
    end
    % Independent MATLAB computation from original AST.
    result = eval_ast(item.expression, item.substitution);
    % Actual structured SageMath result is imported and compared exactly.
    imported = eval_ast(upstream.result, struct());
    if ~isAlways(result == imported)
        error('Independent MATLAB/SageMath mismatch');
    end
    [num, den] = numden(result);
    [sn, sd] = numden(imported);
    results(i).case_id = item.case_id;
    results(i).input_sha256 = meta.input_sha256;
    results(i).metadata_sha256 = meta.metadata_sha256;
    results(i).unit = item.unit;
    results(i).upstream_result = struct('op', 'rational', ...
        'numerator', char(sn), 'denominator', char(sd));
    results(i).result = struct('op', 'rational', ...
        'numerator', char(num), 'denominator', char(den));
end
out = struct('schema', 'math-ir-phase3/1', 'engine', 'MATLAB', ...
             'bundle_sha256', manifest.bundle_sha256, 'results', results);
outFile = fullfile(folder, 'matlab_result.json');
fid = fopen(outFile, 'w');
if fid == -1, error('Cannot open output file'); end
cleaner = onCleanup(@() fclose(fid));
fwrite(fid, jsonencode(out), 'char');
clear cleaner;
fprintf('MATLAB_PH3: generated %d exact results with SageMath input.\n', numCases);
end

function result = eval_ast(node, substitution)
    switch char(node.op)
        case 'integer'
            result = sym(char(node.value));
        case 'rational'
            result = sym(char(node.numerator)) / sym(char(node.denominator));
        case 'symbol'
            name = char(node.name);
            if ~isfield(substitution, name)
                error('Unknown symbol or missing substitution');
            end
            result = eval_ast(substitution.(name), struct());
        case {'add', 'mul', 'pow'}
            if numel(node.args) ~= 2, error('Nonbinary operation'); end
            first = eval_ast(node.args(1), substitution);
            second = eval_ast(node.args(2), substitution);
            switch char(node.op)
                case 'add'
                    result = first + second;
                case 'mul'
                    result = first * second;
                otherwise
                    % Exponent range constrained by the pre-validation step.
                    result = first ^ second;
            end
        otherwise
            error('Unsupported Math IR operation');
    end
end
