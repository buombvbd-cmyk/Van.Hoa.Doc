    r=Reader.query.get_or_404(reader_id); img=qrcode.make(f'READER:{r.code}'); out=BytesIO(); img.save(out,format='PNG'); out.seek(0); return send_file(out,mimetype='image/png')

@app.route('/readers/<int:reader_id>/reading-profile')
def reading_profile(reader_id):
    if not logged_in(): return redirect(url_for('login'))
    r=Reader.query.get_or_404(reader_id); refresh_badges(r.id); return render_template('reading_profile.html',reader=r,books_read=books_read(r.id),points=total_reading_points(r.id),badges=Badge.query.filter_by(reader_id=r.id).order_by(Badge.earned_at).all(),activities=ReadingActivity.query.filter_by(reader_id=r.id).order_by(ReadingActivity.id.desc()).all(),rewards=Reward.query.filter_by(reader_id=r.id).order_by(Reward.id.desc()).all(),loans=Loan.query.filter_by(reader_id=r.id).order_by(Loan.id.desc()).all())

@app.route('/readers/<int:reader_id>/card')
def reader_card(reader_id):
    if not logged_in(): return redirect(url_for('login'))
    return render_template('reader_card.html',reader=Reader.query.get_or_404(reader_id))

@app.route('/loans')
def loans():
    if not logged_in(): return redirect(url_for('login'))
    q=request.args.get('q','').strip(); status=request.args.get('status','all')
    query=Loan.query.join(Book).join(Reader)
    if q:
        like=f'%{q}%'; query=query.filter(db.or_(Book.title.ilike(like),Book.code.ilike(like),Reader.name.ilike(like),Reader.code.ilike(like)))
    if status == 'active': query=query.filter(Loan.status=='Đang mượn')
    elif status == 'returned': query=query.filter(Loan.status=='Đã trả')
    elif status == 'overdue': query=query.filter(Loan.status=='Đang mượn', Loan.due_date < date.today())
    data=query.order_by(Loan.id.desc()).all()
    return render_template('loans.html',loans=data,q=q,status=status,is_overdue=is_overdue)

@app.route('/loans/add', methods=['GET','POST'])
def add_loan():
    if not logged_in(): return redirect(url_for('login'))
    if request.method=='POST':
        try:
            book=Book.query.get(int(request.form['book_id'])); reader=Reader.query.get(int(request.form['reader_id']))
            if not book or not reader: raise ValueError('Sách hoặc bạn đọc không tồn tại.')
            if book.quantity <= 0: raise ValueError('Sách đã hết.')
            if Loan.query.filter_by(reader_id=reader.id,status='Đang mượn').count() >= 5: raise ValueError('Bạn đọc đã đạt tối đa 5 sách đang mượn.')
            due=date.today()+timedelta(days=int(request.form.get('days') or 14)); db.session.add(Loan(book_id=book.id,reader_id=reader.id,borrow_date=date.today(),due_date=due)); book.quantity-=1; db.session.commit(); flash('Đã lập phiếu mượn.','success'); return redirect(url_for('loans'))
        except Exception as e: db.session.rollback(); flash(str(e),'error')
    return render_template('loan_form.html',books=Book.query.filter(Book.quantity>0).order_by(Book.title).all(),readers=Reader.query.order_by(Reader.name).all())

@app.route('/loans/return/<int:loan_id>', methods=['POST'])
def return_loan(loan_id):
    if not logged_in(): return redirect(url_for('login'))
    l=Loan.query.get_or_404(loan_id)
    if l.status=='Đã trả': flash('Phiếu này đã trả.','error'); return redirect(url_for('loans'))
    l.status='Đã trả'; l.return_date=date.today(); l.book.quantity+=1; db.session.commit(); award_return_points(l); flash('Đã trả sách và cộng 20 điểm Văn hóa Đọc.','success'); return redirect(url_for('loans'))

@app.route('/quick-borrow', methods=['GET','POST'])
def quick_borrow():
    if not logged_in(): return redirect(url_for('login'))
    if request.method=='POST':
        code=request.form.get('code','').strip(); book=Book.query.filter_by(code=code).first(); reader=Reader.query.filter_by(code=request.form.get('reader_code','').strip()).first()
        if not book or not reader: flash('Không tìm thấy mã sách hoặc mã bạn đọc.','error')
        elif book.quantity<=0: flash('Sách đã hết.','error')
        elif Loan.query.filter_by(reader_id=reader.id,status='Đang mượn').count()>=5: flash('Bạn đọc đã đạt tối đa 5 sách.','error')
        else:
            db.session.add(Loan(book_id=book.id,reader_id=reader.id,borrow_date=date.today(),due_date=date.today()+timedelta(days=14)))
            book.quantity-=1
            db.session.commit()
            flash('Mượn nhanh thành công.','success')
    return render_template('quick_borrow.html')

@app.route('/quick-return', methods=['GET','POST'])
def quick_return():
    if not logged_in(): return redirect(url_for('login'))
    if request.method=='POST':
        code=request.form.get('code','').strip(); reader_code=request.form.get('reader_code','').strip(); q=Loan.query.join(Book).join(Reader).filter(Loan.status=='Đang mượn')
        if code: q=q.filter(Book.code==code)
        if reader_code: q=q.filter(Reader.code==reader_code)
        l=q.order_by(Loan.id.asc()).first()
        if not l: flash('Không tìm thấy phiếu mượn đang hoạt động.','error')
        else: l.status='Đã trả'; l.return_date=date.today(); l.book.quantity+=1; db.session.commit(); award_return_points(l); flash('Trả nhanh thành công và cộng 20 điểm.','success')
    return render_template('quick_return.html')

@app.route('/shelves')
def shelves():
    if not logged_in(): return redirect(url_for('login'))
    return render_template('shelves.html',shelves=Shelf.query.order_by(Shelf.code).all())

@app.route('/shelves/add', methods=['GET','POST'])
def add_shelf():
    if not logged_in(): return redirect(url_for('login'))
    if request.method=='POST':
        try: db.session.add(Shelf(code=request.form['code'].strip(),name=request.form['name'].strip(),zone=request.form.get('zone'),note=request.form.get('note'))); db.session.commit(); flash('Đã thêm kệ.','success'); return redirect(url_for('shelves'))
        except Exception as e: db.session.rollback(); flash(f'Lỗi: {e}','error')
    return render_template('shelf_form.html',shelf=None)

@app.route('/shelves/edit/<int:shelf_id>', methods=['GET','POST'])
def edit_shelf(shelf_id):
    if not logged_in(): return redirect(url_for('login'))
    s=Shelf.query.get_or_404(shelf_id)
    if request.method=='POST':
        try: s.code=request.form['code'].strip(); s.name=request.form['name'].strip(); s.zone=request.form.get('zone'); s.note=request.form.get('note'); db.session.commit(); flash('Đã cập nhật kệ.','success'); return redirect(url_for('shelves'))
        except Exception as e: db.session.rollback(); flash(f'Lỗi: {e}','error')
    return render_template('shelf_form.html',shelf=s)

@app.route('/shelves/delete/<int:shelf_id>', methods=['POST'])
def delete_shelf(shelf_id):
    if not logged_in(): return redirect(url_for('login'))
    s=Shelf.query.get_or_404(shelf_id); db.session.delete(s); db.session.commit(); flash('Đã xóa kệ.','success'); return redirect(url_for('shelves'))

@app.route('/classes')
def classes():
    if not logged_in(): return redirect(url_for('login'))
    names=[x[0] for x in db.session.query(Reader.class_name).filter(Reader.class_name.isnot(None),Reader.class_name!='').distinct().order_by(Reader.class_name).all()]
    data=[]
    for name in names:
        rs=Reader.query.filter_by(class_name=name).all(); data.append({'name':name,'readers':len(rs),'books':sum(books_read(r.id) for r in rs),'points':sum(total_reading_points(r.id) for r in rs)})
    return render_template('classes.html',classes=data)

@app.route('/reports')
def reports():
    if not logged_in(): return redirect(url_for('login'))
    return render_template('reports.html',total_books=Book.query.count(),copies=sum(b.quantity for b in Book.query.all()),readers=Reader.query.count(),loans=Loan.query.count(),active=Loan.query.filter_by(status='Đang mượn').count(),overdue=Loan.query.filter(Loan.status=='Đang mượn',Loan.due_date<date.today()).count(),points=db.session.query(db.func.coalesce(db.func.sum(ReadingPointsLog.points),0)).scalar() or 0)

@app.route('/reading-culture')
def reading_culture():
    if not logged_in(): return redirect(url_for('login'))
    cls=request.args.get('class','').strip(); query=Reader.query
    if cls: query=query.filter_by(class_name=cls)
    rows=[]
    for r in query.all():
        rows.append({'reader':r,'books':books_read(r.id),'points':total_reading_points(r.id),'badges':Badge.query.filter_by(reader_id=r.id).count()})
    rows.sort(key=lambda x:(-x['points'],-x['books'],x['reader'].name.lower()))
    for i,row in enumerate(rows,1): row['rank']=i
    return render_template('reading_culture.html',rows=rows,classes=class_names(),selected_class=cls)

@app.route('/reading/activities/add', methods=['POST'])
def add_activity():
    if not logged_in(): return redirect(url_for('reading_culture'))
    reader=Reader.query.get_or_404(int(request.form['reader_id']))
    typ=request.form.get('activity_type') or 'Khác'
    pts=max(0,int(request.form.get('points') or ACTIVITY_POINTS.get(typ,5)))
    status='Đã duyệt' if session.get('role')=='admin' else 'Chờ duyệt'
    db.session.add(ReadingActivity(reader_id=reader.id,activity_type=typ,title=request.form['title'].strip(),description=request.form.get('description'),points=pts,status=status))
    db.session.commit()
    flash('Đã ghi nhận hoạt động Văn hóa Đọc.' + (' Chờ duyệt.' if status=='Chờ duyệt' else ''),'success')
    return redirect(url_for('reading_profile',reader_id=reader.id))

@app.route('/reading/activities/<int:activity_id>/approve', methods=['POST'])
def approve_activity(activity_id):
    if not logged_in() or session.get('role')!='admin': abort(403)
    a=ReadingActivity.query.get_or_404(activity_id); a.status='Đã duyệt'; db.session.commit(); flash('Đã duyệt hoạt động.','success'); return redirect(url_for('reading_profile',reader_id=a.reader_id))

@app.route('/reading/activities/<int:activity_id>/reject', methods=['POST'])
def reject_activity(activity_id):
    if not logged_in() or session.get('role')!='admin': abort(403)
    a=ReadingActivity.query.get_or_404(activity_id); a.status='Từ chối'; db.session.commit(); flash('Đã từ chối hoạt động.','success'); return redirect(url_for('reading_profile',reader_id=a.reader_id))

@app.route('/reading/rewards/add', methods=['POST'])
def add_reward():
    if not logged_in(): return redirect(url_for('reading_culture'))
    reader=Reader.query.get_or_404(int(request.form['reader_id'])); db.session.add(Reward(reader_id=reader.id,title=request.form['title'].strip(),description=request.form.get('description'),points=int(request.form.get('points') or 0))); db.session.commit(); flash('Đã ghi nhận khen thưởng.','success'); return redirect(url_for('reading_profile',reader_id=reader.id))


@app.route('/reports/export')
def reports_export():
    if not logged_in(): return redirect(url_for('login'))
    wb=Workbook(); ws=wb.active; ws.title='Tong quan'
    ws.append(['Chỉ tiêu','Giá trị'])
    ws.append(['Đầu sách',Book.query.count()]); ws.append(['Tổng bản sách',sum(b.quantity for b in Book.query.all())])
    ws.append(['Bạn đọc',Reader.query.count()]); ws.append(['Phiếu mượn',Loan.query.count()]); ws.append(['Đang mượn',Loan.query.filter_by(status='Đang mượn').count()])
    ws.append(['Quá hạn',Loan.query.filter(Loan.status=='Đang mượn',Loan.due_date<date.today()).count()])
    ws.append(['Điểm Văn hóa Đọc',sum(total_reading_points(r.id) for r in Reader.query.all())])
    out=BytesIO(); wb.save(out); out.seek(0)
    return send_file(out,as_attachment=True,download_name='bao_cao_thu_vien.xlsx',mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/classes/export')
def classes_export():
    if not logged_in(): return redirect(url_for('login'))
    names=[x[0] for x in db.session.query(Reader.class_name).filter(Reader.class_name.isnot(None),Reader.class_name!='').distinct().order_by(Reader.class_name).all()]
    wb=Workbook(); ws=wb.active; ws.title='Theo lop'; ws.append(['Lớp','Bạn đọc','Lượt đọc','Điểm'])
    for name in names:
        rs=Reader.query.filter_by(class_name=name).all(); ws.append([name,len(rs),sum(books_read(r.id) for r in rs),sum(total_reading_points(r.id) for r in rs)])
    out=BytesIO(); wb.save(out); out.seek(0)
    return send_file(out,as_attachment=True,download_name='bao_cao_lop.xlsx',mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/books/<int:book_id>/history')
def book_history(book_id):
    if not logged_in(): return redirect(url_for('login'))
    b=Book.query.get_or_404(book_id)
    return render_template('book_history.html',book=b,loans=Loan.query.filter_by(book_id=b.id).order_by(Loan.id.desc()).all())

if __name__ == '__main__':
    print('Website QUẢN LÍ THƯ VIỆN đang chạy')
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=False)
