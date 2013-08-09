import cherrypy
import json
from wordtrellis import *
import pprint
import os
import kid

def decor_diff(change_list, txt):
    def decor(change):
        if change[0] == "add":
            return dict(change_type = "add",
                        s = change[1],
                        e = change[2],
                        txt = txt[change[1]:change[2]])
        elif change[0] == "change":
            return dict(change_type = "change",
                        s = change[1],
                        e = change[2],
                        txt = txt[change[1]:change[2]])
        elif change[0] == "delete":
            return dict(change_type = "delete",
                        s = change[1],
                        e = change[2],
                        txt = u"")
    return map(decor, change_list)

def answer_diff(old, new):
    def mk_s_idx(ans):
        idx = {}
        for b in ans.get_boundaries():
            idx[b.get_element().get_s()] = b
        return idx
    old_s_idx = mk_s_idx(old)
    new_s_idx = mk_s_idx(new)
    diff = []
    #find old tok that must be updated
    for old_b in old.get_boundaries():
        if not new_s_idx.has_key(old_b.get_element().get_s()):
            diff.append(
                ("delete", 
                 old_b.get_element().get_s(), 
                 old_b.get_element().get_e()))
        elif old_b.get_element().get_e() != \
                new_s_idx[old_b.get_element().get_s()].get_element().get_e():
            diff.append(
                ("change", 
                 old_b.get_element().get_s(), 
                 new_s_idx[old_b.get_element().get_s()].get_element().get_e()))
    for new_b in new.get_boundaries():
        if not old_s_idx.has_key(new_b.get_element().get_s()):
            diff.append(
                ("add", 
                 new_b.get_element().get_s(), 
                 new_b.get_element().get_e()))
    return diff

def answer_all_positions(answer):
    sidx = {}
    for b in answer.get_boundaries():
        sidx[b.get_element().get_s()] = b

    def convert(i):
        if sidx.has_key(i):
            b = sidx[i]
            return dict(
                s = i,
                valid = True,
                e = b.get_element().get_e(),
                text = answer.get_trellis().get_text(b.get_element()))
        else:
            return dict(s = i, valid = False)

    return map(convert, range(len(answer.get_trellis().get_text())))

def answer_to_text(answer):
    return "|".join([answer.get_trellis().get_text(b.get_element()) 
                        for b in answer.get_boundaries()])

def simplify_answer(answer):
    return [dict(text=answer.get_trellis().get_text(b.get_element()),
                 s = b.get_element().get_s(),
                 e = b.get_element().get_e()) 
                    for b in answer.get_boundaries()]

def simplify_choices(choices, answer):
    return [dict(text = answer.get_trellis().get_text(element),
                 s = element.get_s(),
                 e = element.get_e())
                    for element in choices]
                    
def choice_cmp_func(a, b):
    xa = 10000000 if a[1] == 0 else -a[1]
    xb = 10000000 if b[1] == 0 else -b[1]
    r = cmp(xa, xb)
    if r != 0:
        return r
    len_a = a[0].get_e() - a[0].get_s()
    len_b = b[0].get_e() - a[0].get_s()
    return cmp(len_a, len_b)

class AnnotEdWSeg(object):    
    @cherrypy.expose
    def index(self):        
        return open('editor.html').read()
    
    @cherrypy.expose
    def analyze(self, text):                
        analyzer = get_pruned_analyzer()
        answer_finder = get_simple_answer_finder()
        trellis = analyzer.analyze(text)
        answer = answer_finder.find_answer(trellis)
        cherrypy.session['answer'] = answer
        all_positions_answer = answer_all_positions(answer)                
        return json.dumps(all_positions_answer)
    
    @cherrypy.expose
    def choices(self, s):    
        if cherrypy.session.has_key("answer"):            
            choices_generator = get_rerank_pruned_choices_generator(choice_cmp_func)        
            answer = cherrypy.session['answer']
            s = int(s)
            choices = choices_generator.get_choices(answer, s)
            return json.dumps(simplify_choices(choices, answer))
        else:
            return json.dumps(dict(choices = None))
    
    @cherrypy.expose        
    def select(self, s, e):
        if cherrypy.session.has_key("answer"):
            answer = cherrypy.session['answer']
            updater = get_simple_answer_updater()            
            s = int(s)
            e = int(e)
            new_answer = updater.select(answer, s, e)
            cherrypy.session['answer'] = new_answer
            return json.dumps(dict(success = True, answer=answer_all_positions(new_answer)))
        else:
            return json.dumps(dict(success = False))
            
cherrypy.config.update(os.path.join(os.path.dirname(__file__),"dev.cfg"))
cherrypy.quickstart(AnnotEdWSeg())